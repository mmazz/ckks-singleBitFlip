#!/usr/bin/env python3
"""
Plaintext training of the 784-64-10 MLP used as the encrypted-inference workload.

The activation is selectable with --activation.  Both options are polynomials,
both are trained WITH a BatchNorm1d that is folded into fc1 at export time
(zero cost in the encrypted circuit), and both are exported with the CKKS scale
calibrated so that every intermediate ciphertext stays near magnitude 1.

    x2      a(z) = z^2                    1 ct-ct mult   -> total depth 3
    tanh    a(z) = 0.98 z - 0.23 z^3      2 ct-ct mults  -> total depth 4
            (the usual cubic fit of tanh on [-1, 1])

Exported circuit (what the CKKS evaluator must run)
---------------------------------------------------
x2:
    z = W1 . x + b1     plaintext-ciphertext matmul        (1 level)
    a = z * z           ct-ct mult + relin + rescale       (1 level)
    y = W2 . a + b2     plaintext-ciphertext matmul        (1 level)

tanh:
    z = W1 . x + b1                                        (1 level)
    t = z * z                                              (1 level)
    a = z * (t + k)     k is a PLAINTEXT constant, so the
                        addition is free                   (1 level)
    y = W2 . a + b2                                        (1 level)

W1, b1, W2, b2, k are the EXPORTED tensors: BatchNorm already folded in and the
scale already calibrated.  Never export model.fc1.weight directly - those were
trained with the BatchNorm in the graph and are meaningless without it.

Usage
-----
    python3 trainingNeuralNetwork.py --activation x2
    python3 trainingNeuralNetwork.py --activation tanh --out data/weights_tanh
"""

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader


# --------------------------------------------------------------------------- #
# 1. Activations                                                                #
#                                                                               #
#    Each activation knows three things: how to evaluate itself in torch, how   #
#    to turn the folded weights into a CALIBRATED circuit, and how to run that  #
#    circuit.  Adding a new polynomial activation = adding one class here.      #
#                                                                               #
#    Calibration is the reparametrisation z' = z / s.  It is EXACT (same        #
#    function up to float error) and it is what lets us push |z'| <= 1 so the   #
#    CKKS scale is spent on precision instead of on magnitude.  The scale is    #
#    absorbed by plaintext data (W2, and the constant k), never by an extra     #
#    ciphertext operation, so calibration costs zero levels.                    #
# --------------------------------------------------------------------------- #
class Activation:
    name: str
    coeffs: dict        # {degree: coefficient} of the activation used in training
    ct_ct_levels: int   # ciphertext-ciphertext multiplications needed
    eval_form: str      # how the evaluator should schedule those mults

    def __call__(self, z):
        raise NotImplementedError

    def calibrate(self, W1, b1, W2, b2, s):
        """Folded weights -> circuit parameters for the variable z' = z / s."""
        raise NotImplementedError

    def circuit(self, x, P):
        """Run the exported circuit.  Returns every intermediate ciphertext."""
        raise NotImplementedError

    def exported_coeffs(self, P):
        """a(z') = sum_i c_i z'^i, as [c0, c1, c2, c3]."""
        raise NotImplementedError


class Square(Activation):
    name = "x2"
    coeffs = {2: 1.0}
    ct_ct_levels = 1
    eval_form = "a = z * z"

    def __call__(self, z):
        return z * z

    def calibrate(self, W1, b1, W2, b2, s):
        #   z^2 = s^2 (z/s)^2      -> the whole scale goes into W2.
        # A pure monomial is homogeneous, which is why this is a one-liner.
        return {"W1": W1 / s, "b1": b1 / s, "W2": W2 * (s * s), "b2": b2.clone(),
                "k": None, "s": s}

    def circuit(self, x, P):
        z = x @ P["W1"].T + P["b1"]
        a = z * z
        return {"z": z, "a": a, "logits": a @ P["W2"].T + P["b2"]}

    def exported_coeffs(self, P):
        return [0.0, 0.0, 1.0, 0.0]


class CubicTanh(Activation):
    """a(z) = c1 z + c3 z^3, the degree-3 fit of tanh on [-1, 1]."""

    name = "tanh"
    C1, C3 = 0.98, -0.23
    coeffs = {1: C1, 3: C3}
    ct_ct_levels = 2
    eval_form = "t = z * z ; a = z * (t + k)"

    def __call__(self, z):
        return self.C1 * z + self.C3 * z * z * z

    def calibrate(self, W1, b1, W2, b2, s):
        # This polynomial is NOT homogeneous, so the x^2 trick (divide W1 by s,
        # multiply W2 by s^2) does not preserve the function.  But writing it in
        # Horner form and folding the leading coefficient into the input scale
        # recovers the same freedom, exactly:
        #
        #   c1 z + c3 z^3   with z = s z'
        #     = c1 s z' + c3 s^3 z'^3
        #     = (c3 s^3) . z' . (z'^2 + c1 / (c3 s^2))
        #     =     A    . z' . (z'^2 +        k     )
        #
        # A is plaintext -> folded into W2.  k is plaintext -> a free addition.
        # Cost: 2 ct-ct mults, no plaintext mult, no extra level for the scale.
        A = self.C3 * s ** 3
        k = self.C1 / (self.C3 * s * s)
        return {"W1": W1 / s, "b1": b1 / s, "W2": W2 * A, "b2": b2.clone(),
                "k": k, "s": s}

    def circuit(self, x, P):
        z = x @ P["W1"].T + P["b1"]
        t = z * z
        a = z * (t + P["k"])
        return {"z": z, "t": t, "a": a, "logits": a @ P["W2"].T + P["b2"]}

    def exported_coeffs(self, P):
        # a(z') = z'^3 + k z'
        return [0.0, float(P["k"]), 0.0, 1.0]


ACTIVATIONS = {a.name: a for a in (Square(), CubicTanh())}


# --------------------------------------------------------------------------- #
# 2. Dataset                                                                    #
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


# --------------------------------------------------------------------------- #
# 3. Model                                                                      #
# --------------------------------------------------------------------------- #
class HomomorphicMLP(nn.Module):
    """784 -> 64 -> (BN) -> activation -> 10.

    The activation is fixed at construction time on purpose: a `forward(x, act)`
    with a default silently ignores the flag when the training loop calls
    `model(x)`, and you end up exporting an x^2 circuit from a tanh run.
    """

    def __init__(self, act):
        super().__init__()
        self.act = act
        self.fc1 = nn.Linear(784, 64)
        self.bn = nn.BatchNorm1d(64)   # inference-time affine -> folded away
        self.fc2 = nn.Linear(64, 10)

    def forward(self, x):
        return self.fc2(self.act(self.bn(self.fc1(x))))


# --------------------------------------------------------------------------- #
# 4. Helpers                                                                    #
# --------------------------------------------------------------------------- #
@torch.no_grad()
def accuracy(fn, loader, device):
    correct = n = 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        correct += (fn(x).argmax(1) == y).sum().item()
        n += y.size(0)
    return correct / n


@torch.no_grad()
def circuit_stats(act, P, loader, device, ref=None):
    """Accuracy, max |value| of every intermediate ciphertext, and (optionally)
    the max deviation from a reference model - the export self-check."""
    maxabs, correct, n, dmax = {}, 0, 0, 0.0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        out = act.circuit(x, P)
        for key, t in out.items():
            if key != "logits":
                maxabs[key] = max(maxabs.get(key, 0.0), t.abs().max().item())
        correct += (out["logits"].argmax(1) == y).sum().item()
        n += y.size(0)
        if ref is not None:
            dmax = max(dmax, (out["logits"] - ref(x)).abs().max().item())
    return {"acc": correct / n, "maxabs": maxabs, "logit_maxdiff": dmax}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--activation", choices=sorted(ACTIVATIONS), default="x2",
                    help="polynomial activation to train and export (default: x2)")
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    ap.add_argument("--out", type=Path, default=Path("data/weights"),
                    help="where to write weights, circuit.json and golden vectors")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--scale-margin", type=float, default=1.02,
                    help="s = margin * max|z| on train, so unseen inputs stay inside")
    ap.add_argument("--device", default=None)
    args = ap.parse_args()

    act = ACTIVATIONS[args.activation]
    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    OUT = args.out
    OUT.mkdir(parents=True, exist_ok=True)

    train_dataset = MNISTCSV(args.data_dir / "mnist_train.csv")
    test_dataset = MNISTCSV(args.data_dir / "mnist_test.csv")
    # drop_last: BatchNorm1d raises if a trailing batch has a single element
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size,
                              shuffle=True, drop_last=True)
    # same data, no shuffle, no dropping: used for range calibration
    train_eval_loader = DataLoader(train_dataset, batch_size=512, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=512, shuffle=False)

    # ----------------------------------------------------------------------- #
    # Train                                                                     #
    # ----------------------------------------------------------------------- #
    model = HomomorphicMLP(act).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=args.lr)

    print(f"Activation: {act.name}   {act.coeffs}   "
          f"({act.ct_ct_levels} ct-ct level(s))")
    for epoch in range(args.epochs):
        model.train()
        total = 0.0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()
            total += loss.item()
        print(f"Epoch {epoch + 1}/{args.epochs}, "
              f"Loss: {total / len(train_loader):.4f}")

    model.eval()
    acc_bn = accuracy(model, test_loader, device)
    print(f"Accuracy (BN in graph): {acc_bn * 100:.2f}%")

    # ----------------------------------------------------------------------- #
    # Fold BatchNorm into fc1                                                   #
    #                                                                           #
    #   z_n = gamma * (W1 x + b1 - mu) / sqrt(var + eps) + beta                 #
    #       = (s . W1) x + (s . (b1 - mu) + beta),  s = gamma / sqrt(var + eps) #
    #                                                                           #
    # Independent of the activation: it is a linear op sitting before it.       #
    # ----------------------------------------------------------------------- #
    with torch.no_grad():
        bs = model.bn.weight / torch.sqrt(model.bn.running_var + model.bn.eps)
        W1f = model.fc1.weight * bs[:, None]                      # (64, 784)
        b1f = (model.fc1.bias - model.bn.running_mean) * bs + model.bn.bias
        W2f = model.fc2.weight.clone()                            # (10, 64)
        b2f = model.fc2.bias.clone()

    # s = 1 is the folded circuit without calibration: exact, and its max |z| is
    # what the calibration needs.
    P0 = act.calibrate(W1f, b1f, W2f, b2f, 1.0)
    st0 = circuit_stats(act, P0, train_eval_loader, device)
    zmax = max(st0["maxabs"]["z"], 1e-8)
    acc_folded = circuit_stats(act, P0, test_loader, device)["acc"]
    print(f"Accuracy (folded):      {acc_folded * 100:.2f}%")

    # ----------------------------------------------------------------------- #
    # CKKS scale calibration                                                    #
    # ----------------------------------------------------------------------- #
    s = args.scale_margin * zmax
    P = act.calibrate(W1f, b1f, W2f, b2f, s)

    st_tr = circuit_stats(act, P, train_eval_loader, device)
    st_te = circuit_stats(act, P, test_loader, device, ref=model)
    acc_cal = st_te["acc"]

    print(f"CKKS scale s = {s:.4f}" + ("" if P["k"] is None
                                       else f"   poly const k = {P['k']:.6f}"))
    for key in sorted(st_tr["maxabs"]):
        print(f"|{key}| max: train = {st_tr['maxabs'][key]:.4f}, "
              f"test = {st_te['maxabs'][key]:.4f}"
              + ("   (must be <= 1)" if key == "z" else ""))
    print(f"Accuracy (calibrated):  {acc_cal * 100:.2f}%")
    print(f"Export self-check: max |logit(circuit) - logit(model)| = "
          f"{st_te['logit_maxdiff']:.3e}")

    if st_te["maxabs"]["z"] > 1.0:
        print(f"WARNING: |z| = {st_te['maxabs']['z']:.4f} > 1 on test - raise "
              f"--scale-margin.")
    worst = max(v for k, v in st_te["maxabs"].items())
    if worst > 4.0:
        print(f"WARNING: an intermediate ciphertext reaches {worst:.2f}; the "
              f"CKKS scale loses ~{np.log2(worst):.1f} bits of precision there.")
    if st_te["logit_maxdiff"] > 1e-3 * max(1.0, abs(float(b2f.abs().max()))):
        print("WARNING: the exported circuit does not reproduce the trained "
              "model - do NOT run the fault campaign on these weights.")

    # ----------------------------------------------------------------------- #
    # Export - ONLY the folded + calibrated tensors                             #
    # ----------------------------------------------------------------------- #
    for name in ("W1", "b1", "W2", "b2"):
        a = P[name].detach().cpu().numpy().astype(np.float64)
        np.save(OUT / f"{name}.npy", a)
        np.savetxt(OUT / f"{name}.csv", np.atleast_2d(a), delimiter=",",
                   fmt="%.17g")

    # a(z) = sum_i c_i z^i in the CALIBRATED variable, as [c0, c1, c2, c3]
    coeffs = act.exported_coeffs(P)
    np.savetxt(OUT / "act_coeffs.csv", np.atleast_2d(np.array(coeffs)),
               delimiter=",", fmt="%.17g")

    # Golden vectors: run these through the CKKS evaluator BEFORE the fault
    # campaign.  If the decrypted values do not match, the bug is in the
    # evaluator, not a fault.
    with torch.no_grad():
        xg = test_dataset.images[:16].to(device)
        g = act.circuit(xg, P)
    np.savetxt(OUT / "golden_x.csv", xg.cpu().numpy().astype(np.float64),
               delimiter=",", fmt="%.17g")
    for key, t in g.items():
        np.savetxt(OUT / f"golden_{key}.csv",
                   t.cpu().numpy().astype(np.float64), delimiter=",",
                   fmt="%.17g")
    if act.name == "x2":       # legacy alias for the existing evaluator
        np.savetxt(OUT / "golden_z2.csv",
                   g["a"].cpu().numpy().astype(np.float64), delimiter=",",
                   fmt="%.17g")

    depth = 1 + act.ct_ct_levels + 1          # fc1 + activation + fc2
    with open(OUT / "circuit.json", "w") as fh:
        json.dump(
            {
                "arch": [784, 64, 10],
                "activation": act.name,
                "activation_poly_trained": {str(d): c
                                            for d, c in act.coeffs.items()},
                "activation_poly_exported": coeffs,   # [c0, c1, c2, c3] in z
                "activation_degree": max(act.coeffs),
                "activation_levels": act.ct_ct_levels,
                "activation_eval_form": act.eval_form,
                "poly_const_k": P["k"],
                "total_multiplicative_depth": depth,
                "ops": (["z = W1 . x + b1"]
                        + [op.strip() for op in act.eval_form.split(";")]
                        + ["y = W2 . a + b2"]),
                "input_range": [-1.0, 1.0],
                "ckks_scale_s": s,
                "scale_margin": args.scale_margin,
                "max_abs_train": st_tr["maxabs"],
                "max_abs_test": st_te["maxabs"],
                "max_abs_preactivation_train": st_tr["maxabs"]["z"],
                "max_abs_preactivation_test": st_te["maxabs"]["z"],
                "test_accuracy": acc_cal,
                "test_accuracy_bn_in_graph": acc_bn,
                "export_max_logit_error": st_te["logit_maxdiff"],
                "bn_folded": True,
                "layout": "W1.csv is 64x784 row-major: z = W1 @ x + b1;  "
                          "W2.csv is 10x64",
                "golden_vectors": 16,
                "seed": args.seed,
                "epochs": args.epochs,
            },
            fh,
            indent=2,
        )
    torch.save(model.state_dict(), OUT / "model.pt")   # reproducibility only
    print(f"Weights + golden vectors written to {OUT.resolve()}")


if __name__ == "__main__":
    main()
