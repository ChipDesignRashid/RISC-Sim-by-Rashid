# assembler.py
import re
from riscv_defs import *

def parse_register(reg_str):
    if reg_str in ABI_TO_INDEX: return ABI_TO_INDEX[reg_str]
    elif reg_str.startswith('x'): return int(reg_str[1:])
    raise ValueError(f"Invalid register name: {reg_str}")

def parse_assembly(assembly_text):
    source_lines = [line.split('#')[0].strip().lower() for line in assembly_text.strip().split('\n')]

    # --- PASS 1: Build Symbol Table ---
    symbol_table, current_address = {}, 0
    for line in source_lines:
        if not line: continue
        if line.endswith(':'):
            symbol_table[line[:-1]] = current_address
        else:
            op = re.split(r'\s+', line)[0]
            if op == 'li':
                try:
                    imm_val = int(re.split(r'\s+', line.replace(',', ' '))[2], 0)
                    if not (I_TYPE_IMM_MIN <= imm_val <= I_TYPE_IMM_MAX): current_address += 4
                except: current_address += 4
            current_address += 4

    # --- PASS 2: Encode Instructions ---
    machine_code, disassembly, expansion_log = [], {}, []
    current_address = 0
    for line_num, line in enumerate(source_lines):
        if not line or line.endswith(':'): continue
        original_line = line
        line = line.replace(',', ' ')
        parts = re.split(r'\s+', line)
        op = parts[0]

        # Handle Pseudo-Instructions
        if op == 'j': expansion_log.append(f"L{line_num+1}: `j {parts[1]}` -> `jal zero, {parts[1]}`"); parts = ['jal', 'zero', parts[1]]
        elif op == 'mv': expansion_log.append(f"L{line_num+1}: `mv {parts[1]} {parts[2]}` -> `addi {parts[1]}, {parts[2]}, 0`"); parts = ['addi', parts[1], parts[2], '0']
        elif op == 'nop': expansion_log.append(f"L{line_num+1}: `nop` -> `addi zero, zero, 0`"); parts = ['addi', 'zero', 'zero', '0']
        elif op == 'ret': expansion_log.append(f"L{line_num+1}: `ret` -> `jalr zero, ra, 0`"); parts = ['jalr', 'zero', 'ra', '0']
        op = parts[0]

        instr_list = []
        if op == 'li':
            # 'li' is special as it can expand to two instructions
            rd_str, imm = parts[1], int(parts[2], 0)
            if I_TYPE_IMM_MIN <= imm <= I_TYPE_IMM_MAX:
                instr_list.append(('addi', [rd_str, 'zero', str(imm)]))
                expansion_log.append(f"L{line_num+1}: `{original_line}` -> `addi {rd_str}, zero, {imm}`")
            else:
                upper = (imm + 0x800) >> 12
                lower = imm - (upper << 12)
                instr_list.append(('lui', [rd_str, str(upper)]))
                instr_list.append(('addi', [rd_str, rd_str, str(lower)]))
                expansion_log.append(f"L{line_num+1}: `{original_line}` -> `lui {rd_str}, {hex(upper)}`; `addi {rd_str}, {rd_str}, {lower}`")
        else:
            instr_list.append((op, parts[1:]))

        # Encode the instruction(s)
        for instr_name, args in instr_list:
            mc = 0
            # --- ENCODING LOGIC ---
            if instr_name in ['add', 'sub', 'sll', 'slt', 'sltu', 'xor', 'srl', 'sra', 'or', 'and']:
                rd, rs1, rs2 = parse_register(args[0]), parse_register(args[1]), parse_register(args[2])
                funct3_map = {'add':F3_ADD_SUB, 'sub':F3_ADD_SUB, 'sll':F3_SLL, 'slt':F3_SLT, 'sltu':F3_SLTU, 'xor':F3_XOR, 'srl':F3_SRL_SRA, 'sra':F3_SRL_SRA, 'or':F3_OR, 'and':F3_AND}
                funct7_map = {'add':F7_ADD, 'sub':F7_SUB, 'srl':F7_SRL, 'sra':F7_SRA}
                mc = encode_r(funct7_map.get(instr_name, F7_ADD), rs2, rs1, funct3_map[instr_name], rd, OPCODE_REG)
            elif instr_name in ['addi', 'slti', 'sltiu', 'xori', 'ori', 'andi', 'slli', 'srli', 'srai', 'jalr']:
                rd, rs1, imm = parse_register(args[0]), parse_register(args[1]), int(args[2], 0)
                check_imm(imm, I_TYPE_IMM_MIN, I_TYPE_IMM_MAX, instr_name); opcode = OPCODE_JALR if instr_name == 'jalr' else OPCODE_IMM
                funct3_map = {'addi':F3_ADD_SUB, 'slti':F3_SLT, 'sltiu':F3_SLTU, 'xori':F3_XOR, 'ori':F3_OR, 'andi':F3_AND, 'slli':F3_SLL, 'srli':F3_SRL_SRA, 'srai':F3_SRL_SRA, 'jalr':F3_ADD_SUB}
                if instr_name in ['slli', 'srli', 'srai']: mc = encode_r(F7_SRA if instr_name == 'srai' else F7_SRL, imm, rs1, funct3_map[instr_name], rd, OPCODE_IMM)
                else: mc = encode_i(imm, rs1, funct3_map[instr_name], rd, opcode)
            elif instr_name in ['lui', 'auipc']:
                rd, imm = parse_register(args[0]), int(args[1], 0)
                check_imm(imm, U_IMM_MIN, U_IMM_MAX, instr_name)
                opcode = OPCODE_AUIPC if instr_name == 'auipc' else OPCODE_LUI
                mc = encode_u(imm, rd, opcode)
            elif instr_name in ['lw','lb','lh','lbu','lhu']:
                rd, mem_op = parse_register(args[0]), re.match(r'(-?\d+)\((\w+)\)', args[1])
                imm, rs1 = int(mem_op.group(1)), parse_register(mem_op.group(2)); check_imm(imm, I_TYPE_IMM_MIN, I_TYPE_IMM_MAX, instr_name)
                funct3_map = {'lw':F3_LW, 'lb':F3_LB, 'lh':F3_LH, 'lbu':F3_LBU, 'lhu':F3_LHU}
                mc = encode_i(imm, rs1, funct3_map[instr_name], rd, OPCODE_LOAD)
            elif instr_name in ['sw','sb','sh']:
                rs2, mem_op = parse_register(args[0]), re.match(r'(-?\d+)\((\w+)\)', args[1])
                imm, rs1 = int(mem_op.group(1)), parse_register(mem_op.group(2)); check_imm(imm, S_TYPE_IMM_MIN, S_TYPE_IMM_MAX, instr_name)
                funct3_map = {'sw':F3_SW, 'sb':F3_SB, 'sh':F3_SH}
                mc = encode_s(imm, rs2, rs1, funct3_map[instr_name], OPCODE_STORE)
            elif instr_name in ['beq','bne','blt','bge','bltu','bgeu']:
                rs1, rs2, label = parse_register(args[0]), parse_register(args[1]), args[2]
                imm = symbol_table[label] - current_address; check_imm(imm, B_IMM_MIN, B_IMM_MAX, instr_name)
                funct3_map = {'beq':F3_BEQ, 'bne':F3_BNE, 'blt':F3_BLT, 'bge':F3_BGE, 'bltu':F3_BLTU, 'bgeu':F3_BGEU}
                mc = encode_b(imm, rs2, rs1, funct3_map[instr_name], OPCODE_BRANCH)
            elif instr_name == 'jal':
                rd, label = parse_register(args[0]), args[1]
                imm = symbol_table[label] - current_address; check_imm(imm, J_IMM_MIN, J_IMM_MAX, instr_name)
                mc = encode_j(imm, rd, OPCODE_JAL)

            machine_code.append(mc)
            disassembly[current_address] = original_line
            current_address += 4

    return {'machine_code': machine_code, 'disassembly': disassembly}, expansion_log