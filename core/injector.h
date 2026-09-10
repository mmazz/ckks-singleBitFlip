#pragma once
#include <string>
#include <stdint.h>
#include <optional>

struct FaultSpec {
    std::string stage;           // "encode", "encrypt_c0", "mul", ...
    uint32_t op_depth = 0, op_step = 0;
    uint32_t limb = 0, coeff = 0, bit = 0, amountBits = 1;
};

class Injector {
public:
    explicit Injector(std::optional<FaultSpec> f) : f_(std::move(f)) {}

    bool here(std::string_view stage, uint32_t depth = 0, uint32_t step = 0) const {
        return f_ && f_->stage == stage && f_->op_depth == depth && f_->op_step == step;
    }
    uint64_t mask() const {                      // bits [bit, bit+amountBits)
        return ((f_->amountBits >= 64) ? ~0ULL : ((1ULL << f_->amountBits) - 1)) << f_->bit;
    }
    void record(uint64_t before, uint64_t after) {
        if (std::popcount(before ^ after) != int(f_->amountBits))
            throw std::logic_error("se flipearon bits de más/de menos");
        ++fired_;
    }
    void check_fired() const {                   // al final de run_iteration
        if (f_ && fired_ != 1)
            throw std::runtime_error("fault disparado " + std::to_string(fired_) + " veces");
    }
    const FaultSpec& spec() const { return *f_; }
private:
    std::optional<FaultSpec> f_;
    int fired_ = 0;
};
