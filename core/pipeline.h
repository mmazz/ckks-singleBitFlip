#pragma once
#include <vector>
#include <string>

enum class OpType { 
    Add, PMul, Mul, Scalar, Rot, Boot 
};
struct Op {
    OpType type; 
    double param = 0; 
};   // param: amount de rot o escalar

// "add x2; pmul x1; mul x3; scalar 0.5; rot 4; boot"
std::vector<Op> parse_pipeline(const std::string& s);   // expande "xN" en N ops
