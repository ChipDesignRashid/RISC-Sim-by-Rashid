# instruction_examples.py

# --- 1. R-Type Examples ---
# Covers: add, sub, and, or, xor, sll, srl, sra, slt, sltu
R_TYPE_EXAMPLES = """
# === Integer Register-Register (R-Type) Demo ===
# Setup initial values
li t0, 0xF0F0F0F0   # t0 = -252645136
li t1, 0x00FF00FF   # t1 = 16712191
li t2, 5            # t2 = 5 (for shifting)

# --- Arithmetic ---
add t3, t0, t1      # t3 = t0 + t1
sub t4, t1, t0      # t4 = t1 - t0

# --- Logical ---
and s0, t0, t1      # s0 = t0 & t1 (result: 0x00F000F0)
or  s1, t0, t1      # s1 = t0 | t1 (result: 0xFFFFFFF)
xor s2, t0, t1      # s2 = t0 ^ t1 (result: 0xFF0F0FF0)

# --- Shifts ---
sll s3, t1, t2      # s3 = t1 << 5 (Shift Left Logical)
srl s4, t1, t2      # s4 = t1 >> 5 (Shift Right Logical)
sra s5, t0, t2      # s5 = t0 >> 5 (Shift Right Arithmetic, sign extended)

# --- Comparisons ---
slt s6, t0, t1      # s6 = 1 (Signed Less Than: -252M < 16M)
sltu s7, t0, t1     # s7 = 0 (Unsigned Less Than: 0xF0F0... > 0x00FF...)
# The program now ends gracefully.
"""

# --- 2. I-Type Examples ---
# Covers: addi, andi, ori, xori, slti, sltiu, slli, srli, srai
I_TYPE_EXAMPLES = """
# === Integer Immediate (I-Type) Demo ===
# Setup initial values
li t0, 100          # t0 = 100
li t1, 0b11001100   # t1 = 204

# --- Arithmetic ---
addi t2, t0, -30    # t2 = 100 + (-30) = 70
slti t3, t0, 42     # t3 = 0 (100 is not < 42)
sltiu t4, t0, 200   # t4 = 1 (100 < 200)

# --- Logical ---
andi s0, t1, 0x0F   # s0 = t1 & 0x0F (result: 0b1100)
ori  s1, t1, 0x0F   # s1 = t1 | 0x0F (result: 0b11001111)
xori s2, t1, 0xFF   # s2 = t1 ^ 0xFF (result: 0b00110011)

# --- Shifts ---
slli s3, t0, 4      # s3 = 100 << 4 = 1600
srli s4, t0, 2      # s4 = 100 >> 2 = 25
srai s5, t0, 2      # s5 = 100 >> 2 = 25 (positive, same as srli)
# The program now ends gracefully.
"""

# --- 3. Memory Examples ---
# Covers: lw, lh, lb, lhu, lbu, sw, sh, sb
MEMORY_EXAMPLES = """
# === Memory Access Demo ===
# Store a full 32-bit word (0xDEADBEEF) at address 100.
li s0, 100          # Base address
li s1, 0xDEADBEEF
sw s1, 0(s0)

# Store a byte (0xAA) and a halfword (0xCCBB)
li s2, 0xAA
sb s2, 5(s0)        # Store byte at address 105
li s3, 0xCCBB
sh s3, 6(s0)        # Store halfword at address 106

# --- Load the data back ---
lb  t0, 0(s0)       # t0 should be -17 (sign-extended)
lbu t1, 0(s0)       # t1 should be 239 (zero-extended)
lh  t2, 2(s0)       # t2 should be -8531 (sign-extended)
lhu t3, 2(s0)       # t3 should be 57005 (zero-extended)
lw t4, 0(s0)        # t4 should be 0xDEADBEEF
# The program now ends gracefully.
"""

# --- 4. Branch Examples ---
# Covers: beq, bne, blt, bge, bltu, bgeu
BRANCH_EXAMPLES_FULL = """
# === Branching Demo ===
# Final result in a0 should be 42.
  li s0, 10
  li s1, 10
  li s2, 20
  
  # Branch if Equal (TAKEN)
  beq s0, s1, target_eq
  addi a0, zero, 1  # Should be skipped
  
target_eq:
  addi a0, zero, 10 # a0 = 10

  # Branch if Not Equal (TAKEN)
  bne s0, s2, target_ne
  addi a0, a0, 2    # Should be skipped

target_ne:
  addi a0, a0, 5    # a0 = 15
  
  # Branch if Less Than (TAKEN)
  blt s0, s2, target_lt
  addi a0, a0, 3    # Should be skipped

target_lt:
  addi a0, a0, 7    # a0 = 22
  
  # Branch if Greater/Equal (NOT TAKEN)
  bge s2, s0, target_ge
  # This section will be skipped
  li a0, 99
  j final_halt # Jump over the dead code

target_ge:
  addi a0, a0, 20   # a0 = 42
  
final_halt:
# The program now ends gracefully.
"""

# --- 5. Jump and Call Examples ---
# Covers: jal, jalr
JUMP_CALL_EXAMPLES = """
# === Stack and Function Call Demo ===
# --- Main Program ---
li sp, 1000         # Initialize stack pointer
li s0, 50           # Save 50 in s0 to test preservation
jal ra, outer_func  # Call the function

# After return, a0 holds the result and s0 is 50 again.
# The program now ends gracefully.

# --- Outer Function ---
outer_func:
  addi sp, sp, -8   # 1. Prologue: Allocate stack space
  sw ra, 4(sp)      # Save return address
  sw s0, 0(sp)      # Save caller's s0
  
  li s0, 10         # 2. Body: Use s0 for our own purposes
  jal ra, inner_func# Call nested function

  lw s0, 0(sp)      # 3. Epilogue: Restore s0
  lw ra, 4(sp)      # Restore return address
  addi sp, sp, 8    # Deallocate stack space
  jalr zero, ra, 0  # Return

# --- Inner Function ---
inner_func:
  addi a0, zero, 5  # Set return value
  jalr zero, ra, 0  # Return
"""

# --- 6. Upper Immediate Examples ---
# Covers: lui, auipc
U_TYPE_EXAMPLES = """
# === Upper Immediate (U-Type) Demo ===
# 1. Load 0xABCDE into the upper bits of t0
lui t0, 0xABCDE
# Result: t0 = 0xABCDE000

# 2. Use addi to set the lower 12 bits
addi t0, t0, 0x123
# Result: t0 = 0xABCDE123

# 3. Use AUIPC for PC-relative addressing
# Assume this instruction is at address 0x10.
# t1 = 0x10 + (0x10000 << 12) = 0x10000010
auipc t1, 0x10000
# The program now ends gracefully.
"""

# --- 7. Pseudo-Instruction Examples ---
PSEUDO_INSTRUCTION_EXAMPLES = """
# === Pseudo-Instruction Demo ===
  li t0, 123      # Load Immediate (small) -> addi
  li t1, 65536    # Load Immediate (large) -> lui, addi
  
  mv s0, t1       # Move -> addi s0, t1, 0
  
  j end_label     # Unconditional Jump -> jal zero, ...
  
  nop             # No Operation -> addi zero, zero, 0
  
end_label:
  ret             # Return from function -> jalr zero, ra, 0
# The program now ends gracefully.
"""