#pragma once
#include <string>
#include <stdint.h>
#include <optional>
#include <stdexcept>
#include <string_view>

struct FaultSpec {
    std::string stage;
    uint32_t op_depth = 0, op_step = 0;
    uint32_t limb = 0, coeff = 0, bit = 0, amountBits = 1;
};

class Injector {
public:
    static Injector none();
    static Injector fault(const FaultSpec& f);
    static Injector probe(const std::string& stage, uint32_t op_depth);

    bool here(std::string_view stage, uint32_t depth = 0) const;
    bool probing() const;
    const FaultSpec& spec() const;
    uint64_t mask64() const;

    void record(int flipped_bits, int changed_coeffs);
    void record_probe(uint32_t limbs);
    void record_external();
    void finish() const;
    uint32_t probed_limbs() const;

private:
    enum class Mode { None, Fault, Probe } mode_ = Mode::None;
    FaultSpec f_{};
    int fired_ = 0;
    uint32_t limbs_ = 0;
};

static void inject(DCRTPoly& p, bool ntt, Injector& inj) {
    const Format orig = p.GetFormat();
    p.SetFormat(ntt ? Format::EVALUATION : Format::COEFFICIENT);
    auto& towers = p.GetAllElements();

    if (inj.probing()) {
        inj.record_probe(towers.size());
    } else {
        const FaultSpec& f = inj.spec();
        const DCRTPoly before = p;
        auto& t = towers.at(f.limb);
        if (f.coeff >= t.GetLength()) throw std::out_of_range("coeff fuera de rango");
        const uint64_t a = t[f.coeff].ConvertToInt();
        const uint64_t b = a ^ inj.mask64();
        t[f.coeff] = NativeInteger(b);
        inj.record(__builtin_popcountll(a ^ b), count_diff(before, p));
    }
    p.SetFormat(orig);
}

static void inject(ZZX& poly, long N, Injector& inj) {
    if (inj.probing()) { inj.record_probe(1); return; }
    const FaultSpec& f = inj.spec();
    if (f.coeff >= N) throw std::out_of_range("coeff >= N");
    const ZZX before = poly;
    ZZ x = NTL::coeff(poly, f.coeff);
    for (long b = f.bit; b < long(f.bit + f.amountBits); ++b) SwitchBit(x, b);
    SetCoeff(poly, f.coeff, x);
    // flipped: bits en [bit, bit+amount) donde bit(before_coeff, b) != bit(x, b)
    // changed: i en [0, N) donde NTL::coeff(before, i) != NTL::coeff(poly, i)
    inj.record(flipped, changed);
}

