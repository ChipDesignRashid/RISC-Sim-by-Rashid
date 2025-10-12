# riscv_core.py
from riscv_defs import *

def to_signed_32(value):
    """Converts a 32-bit unsigned value to a signed integer."""
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value

def _sign_extend_12(value):
    """Sign-extends a 12-bit value to a full integer."""
    value &= 0xFFF
    if value & 0x800:  # Check the 12th bit (the sign bit)
        return value - 0x1000
    return value

class RiscVCore:
    def __init__(self, mem_size=4096):
        self.mem = bytearray(mem_size)
        self.loaded_program_mc = [] # Store the initial machine code for resets
        self.reset() # Call reset to initialize state

    def reset(self):
        """Resets the CPU state (PC, registers) and reloads program memory."""
        self.regs = [0] * 32
        self.pc = 0
        self.cycles = 0
        # Reload program into memory from our backup
        self.load_program(self.loaded_program_mc)

    def load_program(self, machine_code):
        """Loads machine code into memory and keeps a backup for resets."""
        self.loaded_program_mc = machine_code
        self.mem = bytearray(len(self.mem)) # Clear memory
        for i, code in enumerate(machine_code):
            if code is not None:
                self.mem[i*4:(i*4)+4] = code.to_bytes(4, 'little', signed=False)

    def step(self):
        """Fetches, decodes, and executes a single instruction."""
        if not (0 <= self.pc < len(self.mem) and self.pc % 4 == 0):
            return False # Halt execution if PC is out of bounds or misaligned

        # 1. FETCH
        instr_mc = int.from_bytes(self.mem[self.pc : self.pc+4], 'little')
        if instr_mc == 0: return False # Stop on null instruction (end of program)

        # 2. DECODE
        opcode = instr_mc & OPCODE_MASK
        rd, rs1, rs2 = (instr_mc >> 7)&0x1F, (instr_mc >> 15)&0x1F, (instr_mc >> 20)&0x1F
        funct3, funct7 = (instr_mc >> 12)&0x7, (instr_mc >> 25)&0x7F
        next_pc = self.pc + 4

        # 3. EXECUTE
        if opcode == OPCODE_LUI:
            imm = instr_mc & 0xFFFFF000
            self.regs[rd] = to_signed_32(imm)
        elif opcode == OPCODE_AUIPC:
            imm = instr_mc & 0xFFFFF000
            self.regs[rd] = to_signed_32(self.pc + imm)
        elif opcode == OPCODE_LOAD:
            imm = _sign_extend_12(instr_mc >> 20)
            addr = self.regs[rs1] + imm
            if funct3 == F3_LB:
                if not (0 <= addr < len(self.mem)): return True
                val = self.mem[addr]; self.regs[rd] = val - 0x100 if val & 0x80 else val
            elif funct3 == F3_LH:
                if not (0 <= addr < len(self.mem) - 1): return True
                self.regs[rd] = int.from_bytes(self.mem[addr:addr+2], 'little', signed=True)
            elif funct3 == F3_LW:
                if not (0 <= addr < len(self.mem) - 3): return True
                self.regs[rd] = int.from_bytes(self.mem[addr:addr+4], 'little', signed=True)
            elif funct3 == F3_LBU:
                if not (0 <= addr < len(self.mem)): return True
                self.regs[rd] = self.mem[addr]
            elif funct3 == F3_LHU:
                if not (0 <= addr < len(self.mem) - 1): return True
                self.regs[rd] = int.from_bytes(self.mem[addr:addr+2], 'little', signed=False)
        elif opcode == OPCODE_STORE:
            imm_raw = ((instr_mc >> 25) << 5) | ((instr_mc >> 7) & 0x1F)
            imm = _sign_extend_12(imm_raw)
            addr = self.regs[rs1] + imm
            if funct3 == F3_SB:
                if not (0 <= addr < len(self.mem)): return True
                self.mem[addr] = self.regs[rs2] & 0xFF
            elif funct3 == F3_SH:
                if not (0 <= addr < len(self.mem) - 1): return True
                self.mem[addr:addr+2] = (self.regs[rs2] & 0xFFFF).to_bytes(2, 'little', signed=False)
            elif funct3 == F3_SW:
                if not (0 <= addr < len(self.mem) - 3): return True
                self.mem[addr:addr+4] = (self.regs[rs2] & 0xFFFFFFFF).to_bytes(4, 'little', signed=False)
        elif opcode == OPCODE_IMM:
            imm = _sign_extend_12(instr_mc >> 20)
            shamt = rs2
            if funct3 == F3_ADD_SUB: self.regs[rd] = to_signed_32(self.regs[rs1] + imm)
            elif funct3 == F3_SLT: self.regs[rd] = 1 if self.regs[rs1] < imm else 0
            elif funct3 == F3_SLTU: self.regs[rd] = 1 if (self.regs[rs1] & 0xFFFFFFFF) < (imm & 0xFFFFFFFF) else 0
            elif funct3 == F3_XOR: self.regs[rd] = self.regs[rs1] ^ imm
            elif funct3 == F3_OR: self.regs[rd] = self.regs[rs1] | imm
            elif funct3 == F3_AND: self.regs[rd] = self.regs[rs1] & imm
            elif funct3 == F3_SLL: self.regs[rd] = to_signed_32(self.regs[rs1] << shamt)
            elif funct3 == F3_SRL_SRA:
                if funct7 == F7_SRA: self.regs[rd] = to_signed_32(self.regs[rs1] >> shamt)
                else: self.regs[rd] = to_signed_32((self.regs[rs1] & 0xFFFFFFFF) >> shamt)
        elif opcode == OPCODE_REG:
            val1, val2 = self.regs[rs1], self.regs[rs2]
            if funct3 == F3_ADD_SUB: self.regs[rd] = to_signed_32(val1 - val2) if funct7 == F7_SUB else to_signed_32(val1 + val2)
            elif funct3 == F3_SLL: self.regs[rd] = to_signed_32(val1 << (val2 & 0x1F))
            elif funct3 == F3_SLT: self.regs[rd] = 1 if val1 < val2 else 0
            elif funct3 == F3_SLTU: self.regs[rd] = 1 if (val1 & 0xFFFFFFFF) < (val2 & 0xFFFFFFFF) else 0
            elif funct3 == F3_XOR: self.regs[rd] = val1 ^ val2
            elif funct3 == F3_SRL_SRA:
                if funct7 == F7_SRA: self.regs[rd] = to_signed_32(val1 >> (val2 & 0x1F))
                else: self.regs[rd] = to_signed_32((val1 & 0xFFFFFFFF) >> (val2 & 0x1F))
            elif funct3 == F3_OR: self.regs[rd] = val1 | val2
            elif funct3 == F3_AND: self.regs[rd] = val1 & val2
        elif opcode == OPCODE_BRANCH:
            imm = to_signed_32(((instr_mc&0x80000000)>>19) | ((instr_mc&0x80)<<4) | ((instr_mc>>20)&0x7e0) | ((instr_mc>>7)&0x1e))
            val1, val2 = self.regs[rs1], self.regs[rs2]
            branch_taken = (funct3 == F3_BEQ and val1 == val2) or \
                           (funct3 == F3_BNE and val1 != val2) or \
                           (funct3 == F3_BLT and val1 < val2) or \
                           (funct3 == F3_BGE and val1 >= val2) or \
                           (funct3 == F3_BLTU and (val1 & 0xFFFFFFFF) < (val2 & 0xFFFFFFFF)) or \
                           (funct3 == F3_BGEU and (val1 & 0xFFFFFFFF) >= (val2 & 0xFFFFFFFF))
            if branch_taken: next_pc = self.pc + imm
        elif opcode == OPCODE_JAL:
            imm = to_signed_32(((instr_mc&0x80000000)>>11) | (instr_mc&0xff000) | ((instr_mc>>9)&0x800) | ((instr_mc>>20)&0x7fe))
            if rd != 0: self.regs[rd] = next_pc
            next_pc = self.pc + imm
        elif opcode == OPCODE_JALR:
            imm = _sign_extend_12(instr_mc >> 20) # Corrected this to use 12-bit extension too
            if rd != 0: self.regs[rd] = next_pc
            next_pc = (self.regs[rs1] + imm) & ~1

        self.regs[0] = 0
        self.pc = next_pc
        self.cycles += 1
        return True # Indicate successful step

    def run(self, max_cycles=5000):
        """Continuously steps until the program ends or max_cycles is hit."""
        start_cycles = self.cycles
        while (self.cycles - start_cycles) < max_cycles:
            if not self.step():
                break # Stop if step() indicates the program is done