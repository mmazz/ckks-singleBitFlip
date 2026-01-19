#pragma once
#include <string>
#include <stdexcept>
#include <iomanip>
#include <cstdint>


enum class AttackModeSKA : uint32_t {
    Disabled = 0,
    CompleteInjection = 1,
    RealOnly = 2,
    ImaginaryOnly = 3
};

inline const char* to_string(AttackModeSKA mode) {
    switch (mode) {
        case AttackModeSKA::Disabled: return "Disabled";
        case AttackModeSKA::CompleteInjection: return "CompleteInjection";
        case AttackModeSKA::RealOnly: return "RealOnly";
        case AttackModeSKA::ImaginaryOnly: return "ImaginaryOnly";
    }
    return "Unknown";
}

inline AttackModeSKA parse_attack_mode(uint32_t v) {
    switch (v) {
        case 0: return AttackModeSKA::Disabled;
        case 1: return AttackModeSKA::CompleteInjection;
        case 2: return AttackModeSKA::RealOnly;
        case 3: return AttackModeSKA::ImaginaryOnly;
        default:
            throw std::invalid_argument("Invalid attackModeSKA value");
    }
}
