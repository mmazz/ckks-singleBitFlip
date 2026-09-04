"""
Plaintext training of the 784-64-10 MLP used as the encrypted-inference workload.

Activation: f(x) = x^2  (degree 2, ONE multiplicative level)
Normalisation: BatchNorm1d before the activation, FOLDED into fc1 at export time
               -> zero cost in the encrypted circuit.

Exported circuit (what the CKKS evaluator must run):

    ct1 = W1f . ct_x + b1f      (plaintext-ciphertext matmul, 1 level)
    ct2 = ct1 * ct1             (ct-ct mult + relin + rescale, 1 level)
    ct3 = W2f . ct2 + b2f       (plaintext-ciphertext matmul, 1 level)

Total multiplicative depth = 3 (vs. 4 for a degree-3 activation).
"""

import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader


# --------------------------------------------------------------------------- #
# 1. Dataset                                                                    #
# --------------------------------------------------------------------------- #
class MNISTCSV(Dataset):
    def __init__(self, csv_path):
        data = np.loadtxt(csv_path, delimiter=",", dtype=np.float32)
        self.labels = torch.tensor(data[:, 0], dtype=torch.long)
        # normalise to [-1, 1]
        self.images = torch.tensor((data[:, 1:] / 255.0) * 2.0 - 1.0,
                                   dtype=torch.float32)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return self.images[idx], self.labels[idx]


OUT = Path("data/weights")
OUT.mkdir(parents=True, exist_ok=True)

train_dataset = MNISTCSV("data/mnist_train.csv")
test_dataset = MNISTCSV("data/mnist_test.csv")
# drop_last: BatchNorm1d raises if a trailing batch has a single element
train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True, drop_last=True)
test_loader = DataLoader(test_dataset, batch_size=64, shuffle=False)


# --------------------------------------------------------------------------- #
# 2. Model                                                                      #
# --------------------------------------------------------------------------- #
class HomomorphicMLP(nn.Module):
    """784 -> 64 -> (BN) -> x^2 -> 10."""

    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(784, 64)
        self.bn = nn.BatchNorm1d(64)   # inference-time affine -> folded away
        self.fc2 = nn.Linear(64, 10)

    def forward(self, x):
        x = self.fc1(x)
        x = self.bn(x)
        x = x * x                      # degree-2 activation, 1 CKKS level
        return self.fc2(x)


model = HomomorphicMLP()
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=1e-3)

for epoch in range(10):
    model.train()
    total = 0.0
    for x, y in train_loader:
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad()
        loss = criterion(model(x), y)
        loss.backward()
        optimizer.step()
        total += loss.item()
    print(f"Epoch {epoch + 1}/10, Loss: {total / len(train_loader):.4f}")


# --------------------------------------------------------------------------- #
# 3. Evaluation                                                                 #
# --------------------------------------------------------------------------- #
@torch.no_grad()
def accuracy(fn):
    correct = n = 0
    for x, y in test_loader:
        x, y = x.to(device), y.to(device)
        correct += (fn(x).argmax(1) == y).sum().item()
        n += y.size(0)
    return correct / n


model.eval()
print(f"Accuracy (BN in graph): {accuracy(model) * 100:.2f}%")


# --------------------------------------------------------------------------- #
# 4. Fold BatchNorm into fc1                                                    #
#                                                                               #
#    z_n = gamma * (W1 x + b1 - mu) / sqrt(var + eps) + beta                    #
#        = (s . W1) x + (s . (b1 - mu) + beta),   s = gamma / sqrt(var + eps)   #
# --------------------------------------------------------------------------- #
with torch.no_grad():
    s = model.bn.weight / torch.sqrt(model.bn.running_var + model.bn.eps)
    W1f = model.fc1.weight * s[:, None]                       # (64, 784)
    b1f = (model.fc1.bias - model.bn.running_mean) * s + model.bn.bias
    W2f = model.fc2.weight.clone()                            # (10, 64)
    b2f = model.fc2.bias.clone()


def folded(x, W1, b1, W2, b2):
    z = x @ W1.T + b1
    return (z * z) @ W2.T + b2


print(f"Accuracy (folded):      "
      f"{accuracy(lambda x: folded(x, W1f, b1f, W2f, b2f)) * 100:.2f}%")


# --------------------------------------------------------------------------- #
# 5. CKKS scale calibration                                                     #
#                                                                               #
#    f(x) = x^2 is a pure monomial, so for any s > 0                            #
#        (W1/s) , (b1/s) , (W2 * s^2)                                           #
#    is EXACTLY the same function. We use that freedom to bring the encoded     #
#    magnitudes near 1 and maximise the usable precision of the CKKS scale.     #
#    A polynomial with a linear or constant term does NOT have this property.   #
# --------------------------------------------------------------------------- #
with torch.no_grad():
    xs = train_dataset.images.to(device)                 # full training set
    zmax = (xs @ W1f.T + b1f).abs().max().item()
    s = 1.02 * zmax          # 2% margin so unseen inputs stay inside |z| <= 1
    W1c, b1c, W2c = W1f / s, b1f / s, W2f * (s * s)

    ztr_max = (xs @ W1c.T + b1c).abs().max().item()
    zte_max = (test_dataset.images.to(device) @ W1c.T + b1c).abs().max().item()

print(f"CKKS scale s = {s:.4f}")
print(f"|z| max: train = {ztr_max:.4f}, test = {zte_max:.4f}   (must be <= 1)")
acc_cal = accuracy(lambda x: folded(x, W1c, b1c, W2c, b2f))
print(f"Accuracy (calibrated):  {acc_cal * 100:.2f}%")


# --------------------------------------------------------------------------- #
# 6. Export -- ONLY the folded + calibrated tensors.                            #
#    Never export model.fc1.weight directly: those were trained WITH the        #
#    BatchNorm in the graph and are meaningless without it.                     #
# --------------------------------------------------------------------------- #
EXPORT = {"W1": W1c, "b1": b1c, "W2": W2c, "b2": b2f}
for name, t in EXPORT.items():
    a = t.detach().cpu().numpy().astype(np.float64)
    np.save(OUT / f"{name}.npy", a)
    np.savetxt(OUT / f"{name}.csv", np.atleast_2d(a), delimiter=",", fmt="%.17g")

# Golden vectors: run these through the CKKS evaluator BEFORE the fault campaign.
# If the decrypted values do not match, the bug is in the evaluator, not a fault.
with torch.no_grad():
    xg = test_dataset.images[:16].to(device)
    zg = xg @ W1c.T + b1c
    ag = zg * zg
    lg = ag @ W2c.T + b2f
for name, t in [("golden_x", xg), ("golden_z", zg), ("golden_z2", ag),
                ("golden_logits", lg)]:
    np.savetxt(OUT / f"{name}.csv", t.cpu().numpy().astype(np.float64),
               delimiter=",", fmt="%.17g")

json.dump(
    {
        "arch": [784, 64, 10],
        "activation": "x^2",
        "activation_degree": 2,
        "activation_levels": 1,
        "total_multiplicative_depth": 3,
        "input_range": [-1.0, 1.0],
        "ckks_scale_s": s,
        "max_abs_preactivation_train": ztr_max,
        "max_abs_preactivation_test": zte_max,
        "test_accuracy": acc_cal,
        "bn_folded": True,
        "layout": "W1.csv is 64x784 row-major: z = W1 @ x + b1;  W2.csv is 10x64",
        "golden_vectors": 16,
    },
    open(OUT / "circuit.json", "w"),
    indent=2,
)
torch.save(model.state_dict(), OUT / "model.pt")   # reproducibility only
print(f"Weights + golden vectors written to {OUT.resolve()}")
