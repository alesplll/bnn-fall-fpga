# Vivado 2022.2: create the practical-work-2 RTL and simulation project.
# Run from an ASCII-only checkout path on Windows:
#   vivado.bat -mode batch -source rtl/create_vivado_project.tcl
# FPGA_PART may override the part announced for the course.

set repo_root [file normalize [file join [file dirname [info script]] ..]]
set project_dir [file join $repo_root vivado_pr2]
set part xc7a100tcsg324-1
if {[info exists ::env(FPGA_PART)] && $::env(FPGA_PART) ne ""} {
    set part $::env(FPGA_PART)
}

create_project -force bnn_pr2 $project_dir -part $part
set_property target_language Verilog [current_project]

set rtl_file [file join $repo_root rtl bnn_classifier.v]
set tb_file [file join $repo_root rtl tb_bnn_classifier.v]
set mem_files [glob -nocomplain [file join $repo_root weights *.mem]]
if {[llength $mem_files] == 0} {
    error "No .mem files found in weights/; run python rtl/gen_full_tb.py first"
}

add_files -fileset sources_1 [concat [list $rtl_file] $mem_files]
set_property top bnn_classifier [get_filesets sources_1]
add_files -fileset sim_1 [list $tb_file]
set_property top tb_bnn_classifier [get_filesets sim_1]
set_property verilog_define {FULL_TEST} [get_filesets sim_1]
set_property xsim.simulate.runtime {30 us} [get_filesets sim_1]

update_compile_order -fileset sources_1
update_compile_order -fileset sim_1
puts "Created Vivado 2022.2 project: [file join $project_dir bnn_pr2.xpr]"
puts "Simulation top: tb_bnn_classifier; FULL_TEST checks 2331 vectors."
puts "Run Behavioral Simulation in Vivado and check for PASS in the Tcl console."
