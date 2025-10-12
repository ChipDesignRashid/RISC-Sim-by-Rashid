# riscv_defs.py
# This file contains the architectural definitions for the RV32I instruction set.

# --- Global Constants ---
# ABI Names for registers
ABI_NAMES = ["zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2", "s0", "s1", "a0", "a1", "a2", "a3", "a4", "a5", "a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6"]
ABI_TO_INDEX = {name: i for i, name in enumerate(ABI_NAMES)}
ABI_TO_INDEX["fp"] = 8 # s0 is also the frame pointer

# --- RV32I Opcodes ---
OPCODE_LUI    = 0b0110111
OPCODE_AUIPC  = 0b0010111
OPCODE_LOAD   = 0b0000011
OPCODE_STORE  = 0b0100011
OPCODE_IMM    = 0b0010011
OPCODE_REG    = 0b0110011
OPCODE_BRANCH = 0b1100011
OPCODE_JAL    = 0b1101111
OPCODE_JALR   = 0b1100111

# --- Funct3 Codes (vary by opcode) ---
F3_ADD_SUB  = 0b000
F3_SLL      = 0b001
F3_SLT      = 0b010
F3_SLTU     = 0b011
F3_XOR      = 0b100
F3_SRL_SRA  = 0b101
F3_OR       = 0b110
F3_AND      = 0b111
F3_BEQ      = 0b000
F3_BNE      = 0b001
F3_BLT      = 0b100
F3_BGE      = 0b101
F3_BLTU     = 0b110
F3_BGEU     = 0b111
F3_LB       = 0b000
F3_LH       = 0b001
F3_LW       = 0b010
F3_LBU      = 0b100
F3_LHU      = 0b101
F3_SB       = 0b000
F3_SH       = 0b001
F3_SW       = 0b010

# --- Funct7 Codes (for R-Type ADD/SUB and SRL/SRA) ---
F7_ADD = 0b0000000
F7_SUB = 0b0100000
F7_SRL = 0b0000000
F7_SRA = 0b0100000

# --- Bit Masks for Decoding ---
OPCODE_MASK = 0x0000007F
RD_MASK     = 0x00000F80
RS1_MASK    = 0x000F8000
RS2_MASK    = 0x01F00000
FUNCT3_MASK = 0x00007000
FUNCT7_MASK = 0xFE000000

# --- Immediate Value Limits ---
I_TYPE_IMM_MIN, I_TYPE_IMM_MAX = -2048, 2047
S_TYPE_IMM_MIN, S_TYPE_IMM_MAX = -2048, 2047
B_IMM_MIN, B_IMM_MAX = -4096, 4094 # Must be even
U_IMM_MIN, U_IMM_MAX = 0, 1048575 # 2^20 - 1
J_IMM_MIN, J_IMM_MAX = -1048576, 1048574 # Must be even

# --- Encoder Functions ---
def check_imm(imm, min_val, max_val, instr_name):
    if not (min_val <= imm <= max_val):
        raise ValueError(f"Immediate {imm} out of range for {instr_name}. Expected range [{min_val}, {max_val}].")

def encode_r(funct7, rs2, rs1, funct3, rd, opcode):
    return (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode
def encode_i(imm, rs1, funct3, rd, opcode):
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode
def encode_s(imm, rs2, rs1, funct3, opcode):
    imm = imm & 0xFFF
    imm11_5 = (imm >> 5) & 0x7F; imm4_0 = imm & 0x1F
    return (imm11_5 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (imm4_0 << 7) | opcode
def encode_b(imm, rs2, rs1, funct3, opcode):
    if imm % 2 != 0: raise ValueError("B-type immediate must be even.")
    imm &= 0x1FFF
    imm12 = (imm >> 12) & 0x1; imm10_5 = (imm >> 5) & 0x3F; imm4_1 = (imm >> 1) & 0xF; imm11 = (imm >> 11) & 0x1
    return (imm12 << 31) | (imm10_5 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (imm4_1 << 8) | (imm11 << 7) | opcode
def encode_u(imm, rd, opcode):
    return ((imm & 0xFFFFF) << 12) | (rd << 7) | opcode
def encode_j(imm, rd, opcode):
    if imm % 2 != 0: raise ValueError("J-type immediate must be even.")
    imm &= 0x1FFFFF
    imm20 = (imm >> 20) & 0x1; imm10_1 = (imm >> 1) & 0x3FF; imm11 = (imm >> 11) & 0x1; imm19_12 = (imm >> 12) & 0xFF
    return (imm20 << 31) | (imm19_12 << 12) | (imm11 << 20) | (imm10_1 << 21) | (rd << 7) | opcode

# --- Disassembler Function (for UI) ---
def disassemble(mc, addr=0, symbol_table=None):
    if symbol_table is None: symbol_table = {}

    def to_signed(val, bits):
        if (val >> (bits - 1)) & 1: return val - (1 << bits)
        return val

    opcode = mc & OPCODE_MASK
    rd, rs1, rs2 = (mc>>7)&0x1F, (mc>>15)&0x1F, (mc>>20)&0x1F
    funct3, funct7 = (mc>>12)&0x7, (mc>>25)&0x7F

    if opcode == OPCODE_REG:
        if funct3 == F3_ADD_SUB:
            if funct7 == F7_ADD: return f"add {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {ABI_NAMES[rs2]}"
            if funct7 == F7_SUB: return f"sub {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {ABI_NAMES[rs2]}"
        elif funct3 == F3_SLL: return f"sll {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {ABI_NAMES[rs2]}"
        elif funct3 == F3_SLT: return f"slt {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {ABI_NAMES[rs2]}"
        elif funct3 == F3_SLTU: return f"sltu {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {ABI_NAMES[rs2]}"
        elif funct3 == F3_XOR: return f"xor {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {ABI_NAMES[rs2]}"
        elif funct3 == F3_SRL_SRA:
            if funct7 == F7_SRA: return f"sra {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {ABI_NAMES[rs2]}"
            else: return f"srl {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {ABI_NAMES[rs2]}"
        elif funct3 == F3_OR: return f"or {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {ABI_NAMES[rs2]}"
        elif funct3 == F3_AND: return f"and {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {ABI_NAMES[rs2]}"
    elif opcode == OPCODE_IMM:
        imm = to_signed(mc >> 20, 12)
        shamt = rs2
        if funct3 == F3_ADD_SUB: return f"addi {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {imm}"
        elif funct3 == F3_SLT: return f"slti {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {imm}"
        elif funct3 == F3_SLTU: return f"sltiu {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {imm}"
        elif funct3 == F3_XOR: return f"xori {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {imm}"
        elif funct3 == F3_OR: return f"ori {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {imm}"
        elif funct3 == F3_AND: return f"andi {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {imm}"
        elif funct3 == F3_SLL: return f"slli {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {shamt}"
        elif funct3 == F3_SRL_SRA:
            if funct7 == F7_SRA: return f"srai {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {shamt}"
            else: return f"srli {ABI_NAMES[rd]}, {ABI_NAMES[rs1]}, {shamt}"
    elif opcode == OPCODE_LUI:
        imm = mc & 0xFFFFF000
        return f"lui {ABI_NAMES[rd]}, {imm >> 12}"
    elif opcode == OPCODE_AUIPC:
        imm = mc & 0xFFFFF000
        return f"auipc {ABI_NAMES[rd]}, {imm >> 12}"
    elif opcode == OPCODE_LOAD:
        imm = to_signed(mc >> 20, 12)
        if funct3 == F3_LB: return f"lb {ABI_NAMES[rd]}, {imm}({ABI_NAMES[rs1]})"
        elif funct3 == F3_LH: return f"lh {ABI_NAMES[rd]}, {imm}({ABI_NAMES[rs1]})"
        elif funct3 == F3_LW: return f"lw {ABI_NAMES[rd]}, {imm}({ABI_NAMES[rs1]})"
        elif funct3 == F3_LBU: return f"lbu {ABI_NAMES[rd]}, {imm}({ABI_NAMES[rs1]})"
        elif funct3 == F3_LHU: return f"lhu {ABI_NAMES[rd]}, {imm}({ABI_NAMES[rs1]})"
    elif opcode == OPCODE_STORE:
        imm = to_signed(((mc >> 25) << 5) | ((mc >> 7) & 0x1F), 12)
        if funct3 == F3_SB: return f"sb {ABI_NAMES[rs2]}, {imm}({ABI_NAMES[rs1]})"
        elif funct3 == F3_SH: return f"sh {ABI_NAMES[rs2]}, {imm}({ABI_NAMES[rs1]})"
        elif funct3 == F3_SW: return f"sw {ABI_NAMES[rs2]}, {imm}({ABI_NAMES[rs1]})"
    elif opcode == OPCODE_BRANCH:
        imm_parts = [ (mc>>7)&0x1E, (mc>>20)&0x7E0, (mc>>7)&0x1, (mc>>31)&0x1 ]
        imm = to_signed((imm_parts[0]) | (imm_parts[1]) | (imm_parts[2]<<11) | (imm_parts[3]<<12), 13)
        target_addr = addr + imm
        if funct3 == F3_BEQ: return f"beq {ABI_NAMES[rs1]}, {ABI_NAMES[rs2]}, {hex(target_addr)}"
        elif funct3 == F3_BNE: return f"bne {ABI_NAMES[rs1]}, {ABI_NAMES[rs2]}, {hex(target_addr)}"
        elif funct3 == F3_BLT: return f"blt {ABI_NAMES[rs1]}, {ABI_NAMES[rs2]}, {hex(target_addr)}"
        elif funct3 == F3_BGE: return f"bge {ABI_NAMES[rs1]}, {ABI_NAMES[rs2]}, {hex(target_addr)}"
        elif funct3 == F3_BLTU: return f"bltu {ABI_NAMES[rs1]}, {ABI_NAMES[rs2]}, {hex(target_addr)}"
        elif funct3 == F3_BGEU: return f"bgeu {ABI_NAMES[rs1]}, {ABI_NAMES[rs2]}, {hex(target_addr)}"
    elif opcode == OPCODE_JAL:
        imm_parts = [ (mc>>21)&0x3FF, (mc>>20)&0x1, (mc>>12)&0xFF, (mc>>31)&0x1 ]
        imm = to_signed( (imm_parts[0]<<1) | (imm_parts[1]<<11) | (imm_parts[2]<<12) | (imm_parts[3]<<20), 21)
        target_addr = addr + imm
        return f"jal {ABI_NAMES[rd]}, {hex(target_addr)}"
    elif opcode == OPCODE_JALR:
        imm = to_signed(mc >> 20, 12)
        return f"jalr {ABI_NAMES[rd]}, {imm}({ABI_NAMES[rs1]})"

    return f"; unknown (0x{mc:08x})" # Fallback