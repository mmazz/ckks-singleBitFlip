#include "backend_interface.h"

// HEAAN-only includes
#include "HEAAN.h"
#include <NTL/ZZ.h>
#include <vector>


const size_t MAX_H = 64;
struct HEAANContext : BackendContext {
    Context cc;
    SecretKey sk;
    Scheme scheme;

    std::vector<double> baseInput;
    std::vector<double> goldenOutput;
    NTL::ZZ seed;

    HEAANContext(
        uint32_t logN,
        uint32_t logQ,
        uint32_t h,
        uint64_t seed_
    )
        : cc(logN, logQ)
        , sk(logN, h)
        , scheme(sk, cc)   // ← ahora sí
        , seed(NTL::ZZ(seed_))
    {}

    HEAANContext(const HEAANContext&) = delete;
    HEAANContext& operator=(const HEAANContext&) = delete;
};

const std::vector<double>&
get_reference_output(const BackendContext* bctx)
{
    auto& ctx = static_cast<const HEAANContext&>(*bctx);
    return ctx.goldenOutput;
}

BackendContext* setup_campaign(const CampaignArgs& args)
    {
    long h = pow(2, args.logN);
        if (h > MAX_H)
            h = MAX_H;
    auto* ctx = new HEAANContext(
        args.logN,
        args.logQ,
        h,          // h
        args.seed
    );

    NTL::SetSeed(ctx->seed);
    std::srand(args.seed);
    ctx->baseInput = uniform_dist(
        1 << args.logSlots,
        args.logMin,
        args.logMax,
        args.seed_input,
        false
    );
    ctx->goldenOutput = ctx->baseInput;

    if (args.doAdd && !args.doMul) {
        // golden = base + base
        std::transform(ctx->baseInput.begin(),
                       ctx->baseInput.end(),
                       ctx->baseInput.begin(),
                       ctx->goldenOutput.begin(),
                       std::plus<double>());
    }

    if (args.doMul && !args.doAdd) {
        // golden = base * base
        std::transform(ctx->baseInput.begin(),
                       ctx->baseInput.end(),
                       ctx->baseInput.begin(),
                       ctx->goldenOutput.begin(),
                       std::multiplies<double>());
    }

    if (args.doAdd && args.doMul) {
        // golden = (base + base) * base
        std::transform(ctx->baseInput.begin(),
                       ctx->baseInput.end(),
                       ctx->goldenOutput.begin(),
                       [](double x) {
                           return (x + x) * x;
                       });
    }
    return ctx;
}

IterationResult run_iteration(
    BackendContext* bctx,
    const CampaignArgs& args,
    std::optional<IterationArgs> iterArgs)
{
    // Backend cerrado: cast seguro por contrato
    auto& ctx = static_cast<HEAANContext&>(*bctx);

    /* ---------------- Encode ---------------- */
    Plaintext plain = ctx.scheme.encode(
        ctx.baseInput.data(),
        ctx.baseInput.size(),
        args.logDelta,
        args.logQ
    );

    if (iterArgs && args.stage == "encode") {
        SwitchBit(plain.mx[iterArgs->coeff], iterArgs->bit);
    }

    /* ---------------- Encrypt ---------------- */
    Ciphertext c = ctx.scheme.encryptMsg(plain, ctx.seed);
    Ciphertext c_clean;
    if(args.doAdd || args.doMul)
        c_clean = ctx.scheme.encryptMsg(plain, ctx.seed);



    if (iterArgs) {
        if (args.stage == "encrypt_c0") {
            SwitchBit(c.bx[iterArgs->coeff], iterArgs->bit);
        } else if (args.stage == "encrypt_c1") {
            SwitchBit(c.ax[iterArgs->coeff], iterArgs->bit);
        }
    }

    if(args.doAdd)
        c = ctx.scheme.add(c, c_clean);
    if(args.doMul){
        c = ctx.scheme.mult(c, c_clean);
        ctx.scheme.reScaleByAndEqual(c, args.logDelta);
    }
    /* ---------------- Decrypt ---------------- */
    Plaintext decrypt_plain = ctx.scheme.decryptMsg(ctx.sk, c);

    if (iterArgs && args.stage == "decrypt") {
        SwitchBit(decrypt_plain.mx[iterArgs->coeff], iterArgs->bit);
    }

    /* ---------------- Decode ---------------- */
    complex<double>* decoded = ctx.scheme.decode(decrypt_plain);

    IterationResult res;
    const size_t slots = 1u << args.logSlots;
    res.values.resize(slots);

    for (size_t i = 0; i < slots; i++) {
        res.values[i] = decoded[i].real();
    }

    delete[] decoded;   // 🔴 CRÍTICO: evita memory leak

    res.detected = false;  // placeholder (tu lógica SDC va acá)

    return res;
}

void destroy_campaign(BackendContext* ctx) {
    delete ctx;
}

