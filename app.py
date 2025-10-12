# app.py
import streamlit as st
from assembler import parse_assembly
from riscv_core import RiscVCore
from riscv_defs import ABI_NAMES, ABI_TO_INDEX, disassemble
from instruction_examples import *

INSTRUCTION_SUMMARY_MD = """
#### RV32I Base Instruction Set (37 Instructions)
| Instruction Type | Count | Status & Implemented Instructions |
| :--- | :--- | :--- |
| **R-Type (Register-Register)** | 10 / 10 | ✅ **Complete** <br> `add`, `sub`, `sll`, `slt`, `sltu`, `xor`, `srl`, `sra`, `or`, `and` |
| **I-Type (Immediate)** | 9 / 9 | ✅ **Complete** <br> `addi`, `slti`, `sltiu`, `xori`, `ori`, `andi`, `slli`, `srli`, `srai` |
| **Load** | 5 / 5 | ✅ **Complete** <br> `lw`, `lb`, `lh`, `lbu`, `lhu` |
| **Store** | 3 / 3 | ✅ **Complete** <br> `sw`, `sb`, `sh` |
| **Branch** | 6 / 6 | ✅ **Complete** <br> `beq`, `bne`, `blt`, `bge`, `bltu`, `bgeu` |
| **Jump** | 2 / 2 | ✅ **Complete** <br> `jal`, `jalr` |
| **U-Type (Upper Immediate)**| 2 / 2 | ✅ **Complete** <br> `lui`, `auipc` |
"""

# NEW: Help text content
HELP_DOCUMENTATION_MD = """
Welcome to RISC Sim by Rashid! This is an interactive tool for writing, assembling, and debugging RV32I assembly code.

**How to Use:**
1.  **Write Code:** Type your RISC-V assembly code in the "Assembly Program" text area below.
2.  **Load an Example:** Alternatively, expand "Show References and Examples" to load a pre-written program.
3.  **Assemble & Load:** Click the `▶️ Assemble & Load` button. This converts your assembly into machine code and loads it into the instruction memory.
4.  **Control Execution:**
    * `⏯️ Step`: Execute one instruction at a time.
    * `⏩ Run to End`: Execute the program until it halts or hits the cycle limit.
    * `🔄 Reset`: Reset the processor and memory to the initial state.

**Understanding the UI:**
* **CPU Registers:** Displays all 32 registers. The border colors group them by their ABI role (e.g., arguments, temporary, saved). Non-zero values are highlighted in green.
* **Instruction Memory:** Shows the assembled machine code. The current instruction pointed to by the Program Counter (PC) is highlighted in yellow.
* **Stack Memory:** This view is centered around the Stack Pointer (SP). The address pointed to by SP is highlighted in orange, making it easy to see stack operations.
* **Data Memory:** A general-purpose memory region for your program's data.
"""


# --- UI Helper Functions ---
def load_css(file_name):
    with open(file_name) as f: st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def get_reg_group_class(reg_index):
    if reg_index == 0: return ""
    if reg_index in [1, 2, 3, 4]: return "group-special"
    if reg_index in range(5, 8) or reg_index in range(28, 32): return "group-temp"
    if reg_index in range(8, 10) or reg_index in range(18, 28): return "group-saved"
    if reg_index in range(10, 18): return "group-args"
    return ""

def generate_mem_view(title, memory_bytes, start, length, words_per_row=4, highlights=None, layout='row'):
    if highlights is None: highlights = {}
    html = f'<h4>{title}</h4><div class="mem-view">'

    words_in_view = length // 4
    num_rows = (words_in_view + words_per_row - 1) // words_per_row

    for r in range(num_rows):
        html += '<div class="mem-row">'
        for c in range(words_per_row):
            addr = 0
            if layout == 'col':
                word_index = c * num_rows + r
                addr = start + word_index * 4
            else: # row-major
                word_index = r * words_per_row + c
                addr = start + word_index * 4

            if word_index >= words_in_view or addr + 4 > len(memory_bytes):
                html += '<div class="mem-word-box empty-box"></div>'
                continue

            val = int.from_bytes(memory_bytes[addr:addr+4], 'little', signed=True)
            hex_val = val & 0xFFFFFFFF

            class_list = ["mem-word-box"]
            if val != 0: class_list.append("mem-nonzero")

            for highlight_addr, class_name in highlights.items():
                if addr == highlight_addr:
                    class_list.append(class_name)

            is_instr = "Instruction" in title
            disasm_text = disassemble(hex_val, addr) if is_instr and hex_val != 0 else ""
            sp_label = " &larr; sp" if "sp-highlight" in class_list else ""

            html += f'<div class="{" ".join(class_list)}">'
            html += f'<span class="mem-addr">0x{addr:04x}:</span>'
            html += f'<span class="mem-hex">0x{hex_val:08x}</span>'
            if is_instr: html += f'<span class="mem-disasm">{disasm_text}</span>'
            else: html += f'<span class="sp-label">{sp_label}</span>'
            html += '</div>'
        html += '</div>'
    html += '</div>'
    return html

# --- The Streamlit User Interface ---
st.set_page_config(layout="wide")
# UPDATED: Title
st.title("RISC Sim by Rashid")
load_css("style.css")

# NEW: Help Expander
with st.expander("Quick Help & Documentation"):
    st.markdown(HELP_DOCUMENTATION_MD)

# --- Initialize Session State ---
if 'core' not in st.session_state: st.session_state.core = None
if 'program_info' not in st.session_state: st.session_state.program_info = None
if 'assembly_code' not in st.session_state: st.session_state.assembly_code = JUMP_CALL_EXAMPLES

# --- Callbacks for State Changes ---
def assemble_and_load():
    try:
        program_info, expansion_log = parse_assembly(st.session_state.assembly_code)
        st.session_state.program_info = {'program': program_info, 'log': expansion_log}
        core = RiscVCore()
        core.load_program(program_info['machine_code'])
        st.session_state.core = core
    except Exception as e:
        st.error(f"Assembly Error: {e}")
        st.session_state.core = None

def step_core():
    if st.session_state.core: st.session_state.core.step()

def run_core():
    if st.session_state.core: st.session_state.core.run()

def reset_core():
    if st.session_state.core: st.session_state.core.reset()

with st.expander("Show References and Examples"):
    st.write("**Load Example Programs:**")
    cols1 = st.columns(4)
    if cols1[0].button("Integer (R-Type)", use_container_width=True): st.session_state.assembly_code = R_TYPE_EXAMPLES
    if cols1[1].button("Integer (I-Type)", use_container_width=True): st.session_state.assembly_code = I_TYPE_EXAMPLES
    if cols1[2].button("Memory Ops", use_container_width=True): st.session_state.assembly_code = MEMORY_EXAMPLES
    if cols1[3].button("Branches", use_container_width=True): st.session_state.assembly_code = BRANCH_EXAMPLES_FULL

    cols2 = st.columns(4)
    if cols2[0].button("Jumps & Calls", use_container_width=True): st.session_state.assembly_code = JUMP_CALL_EXAMPLES
    if cols2[1].button("Upper Immediate", use_container_width=True): st.session_state.assembly_code = U_TYPE_EXAMPLES
    if cols2[2].button("Pseudo-Instructions", use_container_width=True): st.session_state.assembly_code = PSEUDO_INSTRUCTION_EXAMPLES

    st.markdown("---")
    with st.popover("📜 Show Instruction Set Summary", use_container_width=True):
        st.markdown(INSTRUCTION_SUMMARY_MD, unsafe_allow_html=True)


st.subheader("Assembly Program")
st.text_area("Enter your code:", key='assembly_code', height=350)

st.markdown("---")
cols = st.columns([1.5, 1, 1, 1])

# --- Control Panel using on_click callbacks ---
cols[0].button("▶️ Assemble & Load", on_click=assemble_and_load, use_container_width=True)
cols[1].button("⏯️ Step", on_click=step_core, use_container_width=True, disabled=st.session_state.core is None)
cols[2].button("⏩ Run to End", on_click=run_core, use_container_width=True, disabled=st.session_state.core is None)
cols[3].button("🔄 Reset", on_click=reset_core, use_container_width=True, disabled=st.session_state.core is None)

st.markdown("---")

# --- Display Area ---
if st.session_state.core:
    core = st.session_state.core
    program_info = st.session_state.program_info

    if program_info['log']:
        st.subheader("Expanded Pseudo-Instructions")
        st.code('\n'.join(program_info['log']), language='plaintext')

    if core.cycles >= 5000:
        st.warning(f"Simulation stopped after reaching the cycle limit of 5000.")

    res_col1, res_col2 = st.columns([1, 2])
    with res_col1:
        st.subheader("CPU Registers")
        html = '<div class="reg-container">'
        for i in range(32):
            val = core.regs[i]
            base_style = get_reg_group_class(i)
            style_class = f"{base_style} {'reg-nonzero' if val != 0 else ''}"
            hex_val = val & 0xFFFFFFFF
            display_val = f"{val} (0x{hex_val:08x})"
            html += f'<div class="reg-box {style_class}">{ABI_NAMES[i]} (x{i})<br><b>{display_val}</b></div>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)
    with res_col2:
        mc_len = len(program_info['program']['machine_code']) * 4
        st.markdown(generate_mem_view("Instruction Memory", core.mem, 0, mc_len, 2, highlights={core.pc: "pc-highlight"}, layout='row'), unsafe_allow_html=True)

        sp_val = core.regs[ABI_TO_INDEX['sp']]
        stack_start = max(0, sp_val - 32) & ~0x3
        st.markdown(generate_mem_view("Stack Memory", core.mem, stack_start, 64, 2, highlights={sp_val: "sp-highlight"}, layout='col'), unsafe_allow_html=True)

        st.markdown(generate_mem_view("Data Memory", core.mem, 512, 256, 4, layout='row'), unsafe_allow_html=True)
else:
    st.info("Assemble & Load a program to begin simulation.")