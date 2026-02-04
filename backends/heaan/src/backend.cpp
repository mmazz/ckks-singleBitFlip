#include "backend_interface.h"

// HEAAN-only includes
#include "HEAAN.h"
#include <NTL/ZZ.h>
#include <vector>
#include <complex>
#include <algorithm>

const size_t MAX_H = 64;

struct HEAANContext : BackendContext {
    Context cc;
    SecretKey sk;
    Scheme scheme;

    std::vector<double> baseInput;
    std::vector<double> goldenOutput;
    std::vector<std::complex<double>> baseInputComplex;
    std::vector<std::complex<double>> goldenOutputComplex;
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

std::vector<double> get_reference_output(const BackendContext* bctx)
{
    auto& ctx = static_cast<const HEAANContext&>(*bctx);
    return ctx.goldenOutput;
}

std::vector<double> get_reference_output_complex(const BackendContext* bctx)
{
    auto& ctx = static_cast<const HEAANContext&>(*bctx);

    const auto& g = ctx.goldenOutputComplex;
    const size_t n = g.size();

    std::vector<double> out(2 * n);

    for (size_t i = 0; i < n; ++i) {
        out[i]     = g[i].real();
        out[i + n] = g[i].imag();
    }

    return out;
}



BackendContext* setup_campaign(const CampaignArgs& args)
{
    long h;
    uint64_t N = 1 << args.logN;
    if (args.logN > 10)
        h = MAX_H;
    else
        h = std::max<long>(1,N/64);

    auto* ctx = new HEAANContext(args.logN, args.logQ, h, args.seed);

    if(args.doRot){
        int32_t rotIndex = static_cast<int32_t>(1ULL << (args.doRot - 1));
        ctx->scheme.addLeftRotKey(ctx->sk, rotIndex);
    }
    NTL::SetSeed(ctx->seed);
    std::srand(args.seed);

    if(args.isComplex){
        compute_plain_io(args, ctx->baseInputComplex, ctx->goldenOutputComplex);
    } else{
        compute_plain_io(args, ctx->baseInput, ctx->goldenOutput);
    }

    return ctx;
}

IterationResult run_iteration(
    BackendContext* bctx,
    const CampaignArgs& args,
    std::optional<IterationArgs> iterArgs)
{
    auto& ctx = static_cast<HEAANContext&>(*bctx);

    auto baseInput = ctx.baseInput.data();
    auto baseInputComplex = ctx.baseInputComplex.data();
    auto baseSize = ctx.baseInput.size();

    if(args.isComplex)
        baseSize = ctx.baseInputComplex.size();

    Plaintext plain;
    Plaintext plain_clean;

    if(args.isComplex){
        plain = ctx.scheme.encode(
            baseInputComplex,
            baseSize,
            args.logDelta,
            args.logQ
        );
    } else{
        plain = ctx.scheme.encode(
            baseInput,
            baseSize,
            args.logDelta,
            args.logQ
        );
    }

    if (iterArgs && args.stage == "encode") {
        SwitchBit(plain.mx[iterArgs->coeff], iterArgs->bit);
    }

    Ciphertext c = ctx.scheme.encryptMsg(plain, ctx.seed);
    Ciphertext c_clean;
    if(args.doAdd || args.doMul){
        if(args.isComplex){
            plain_clean =  ctx.scheme.encode(baseInputComplex,
                                baseSize,
                                args.logDelta,
                                args.logQ
                            );
        } else {
            plain_clean =  ctx.scheme.encode(baseInput,
                                baseSize,
                                args.logDelta,
                                args.logQ
                            );
        }
        c_clean = ctx.scheme.encryptMsg(plain_clean, ctx.seed);
    }

    if(args.doPlainMul){
        if(args.isComplex){
            plain_clean =  ctx.cc.encode(baseInputComplex,
                                baseSize,
                                args.logDelta
                            );
        } else {
            plain_clean =  ctx.cc.encode(baseInput,
                                baseSize,
                                args.logDelta
                            );
        }
    }

    if (iterArgs) {
        if (args.stage == "encrypt_c0") {
            SwitchBit(c.bx[iterArgs->coeff], iterArgs->bit);
        } else if (args.stage == "encrypt_c1") {
            SwitchBit(c.ax[iterArgs->coeff], iterArgs->bit);
        }
    }

    if(args.doAdd)
        c = ctx.scheme.add(c, c_clean);

    for (uint32_t i = 0; i < args.doPlainMul; ++i) {
        c = ctx.scheme.multByPoly(c, plain_clean.mx, args.logDelta);
    }

    for (uint32_t i = 0; i < args.doMul; ++i) {
        c = ctx.scheme.mult(c, c_clean);
        ctx.scheme.reScaleByAndEqual(c, args.logDelta);
        ctx.scheme.reScaleByAndEqual(c_clean, args.logDelta);
    }

    if(args.doRot){
        int32_t rotIndex = static_cast<int32_t>(1ULL << (args.doRot - 1));
        c = ctx.scheme.leftRotateFast(c, rotIndex);
    }

    if (iterArgs) {
        if ((args.stage == "encrypt_c0_eval") && (args.doAdd >0 || args.doPlainMul>0 || args.doMul>0 || args.doRot>0)){
            SwitchBit(c.bx[iterArgs->coeff], iterArgs->bit);
        } else if ((args.stage == "encrypt_c1_eval") && (args.doAdd >0 || args.doPlainMul>0 || args.doMul>0 || args.doRot>0)){
            SwitchBit(c.ax[iterArgs->coeff], iterArgs->bit);
        }
    }

    Plaintext decrypt_plain = ctx.scheme.decryptMsg(ctx.sk, c);

    if (iterArgs && args.stage == "decrypt") {
        SwitchBit(decrypt_plain.mx[iterArgs->coeff], iterArgs->bit);
    }

    complex<double>* decoded = ctx.scheme.decode(decrypt_plain);

    IterationResult res;
    const size_t slots = 1u << args.logSlots;
    if(args.isComplex){
        res.values.resize(2*slots);

        for (size_t i = 0; i < slots; i++) {
            res.values[i] = decoded[i].real();
            res.values[i+slots] = decoded[i].imag();
        }

    } else {
        res.values.resize(slots);

        for (size_t i = 0; i < slots; i++) {
            res.values[i] = decoded[i].real();
        }

    }

    delete[] decoded;

    res.detected = false;

    return res;
}

void destroy_campaign(BackendContext* ctx) {
    delete ctx;
}

IterationResult run_NN(
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
    Plaintext plain_clean;
    if (iterArgs && args.stage == "encode") {
        SwitchBit(plain.mx[iterArgs->coeff], iterArgs->bit);
    }

    Ciphertext c = ctx.scheme.encryptMsg(plain, ctx.seed);
    Ciphertext c_clean;
    if(args.doAdd || args.doMul){
        plain_clean =  ctx.scheme.encode(ctx.baseInput.data(),
                            ctx.baseInput.size(),
                            args.logDelta,
                            args.logQ
                        );
        c_clean = ctx.scheme.encryptMsg(plain_clean, ctx.seed);
    }

    if(args.doPlainMul){
        plain_clean =  ctx.cc.encode(ctx.baseInput.data(),
                            ctx.baseInput.size(),
                            args.logDelta
                        );
    }

    if (iterArgs) {
        if (args.stage == "encrypt_c0") {
            SwitchBit(c.bx[iterArgs->coeff], iterArgs->bit);
        } else if (args.stage == "encrypt_c1") {
            SwitchBit(c.ax[iterArgs->coeff], iterArgs->bit);
        }
    }

    if(args.doAdd)
        c = ctx.scheme.add(c, c_clean);

    for (uint32_t i = 0; i < args.doPlainMul; ++i) {
        c = ctx.scheme.multByPoly(c, plain_clean.mx, args.logDelta);
    }

    for (uint32_t i = 0; i < args.doMul; ++i) {
        c = ctx.scheme.mult(c, c_clean);
        ctx.scheme.reScaleByAndEqual(c, args.logDelta);
    }

    if(args.doRot){
        int32_t rotIndex = static_cast<int32_t>(1ULL << (args.doRot - 1));
        c = ctx.scheme.leftRotateFast(c, rotIndex);
    }

    if (iterArgs) {
        if ((args.stage == "encrypt_c0_eval") && (args.doAdd >0 || args.doPlainMul>0 || args.doMul>0 || args.doRot>0)){
            SwitchBit(c.bx[iterArgs->coeff], iterArgs->bit);
        } else if ((args.stage == "encrypt_c1_eval") && (args.doAdd >0 || args.doPlainMul>0 || args.doMul>0 || args.doRot>0)){
            SwitchBit(c.ax[iterArgs->coeff], iterArgs->bit);
        }
    }

    Plaintext decrypt_plain = ctx.scheme.decryptMsg(ctx.sk, c);

    if (iterArgs && args.stage == "decrypt") {
        SwitchBit(decrypt_plain.mx[iterArgs->coeff], iterArgs->bit);
    }

    complex<double>* decoded = ctx.scheme.decode(decrypt_plain);

    IterationResult res;
    const size_t slots = 1u << args.logSlots;
    res.values.resize(slots);

    for (size_t i = 0; i < slots; i++) {
        res.values[i] = decoded[i].real();
    }

    delete[] decoded;

    res.detected = false;

    return res;
}

