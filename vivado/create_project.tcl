# One Vivado 2022.2 project for the PR2 classifier, PR3 prototype and
# the registered-layer comparison. Source from the repository root.
set repo_root [file normalize [file join [file dirname [info script]] ..]]
set project_dir [file join $repo_root vivado_pr23]
set project_file [file join $project_dir bnn_pr23.xpr]
set part xc7a100tcsg324-1
set clock_file [file join $project_dir clock_run.xdc]

catch {close_sim}
catch {close_project}
if {[file exists $project_file]} {
    open_project $project_file
} else {
    create_project bnn_pr23 $project_dir -part $part
}
if {![file exists $clock_file]} {
    set fd [open $clock_file w]
    puts $fd {create_clock -name clk -period 20.000 [get_ports clk]}
    close $fd
}
if {[get_property PART [current_project]] ne $part} {
    error "Project part must be $part"
}
set_property target_language Verilog [current_project]
set_property target_simulator XSim [current_project]

set design_files [list \
    [file join $repo_root rtl bnn_classifier.v] \
    [file join $repo_root rtl bnn_layer_a.v] \
    [file join $repo_root rtl bnn_layer_b.v] \
    [file join $repo_root rtl bnn_classifier_modular.v] \
    [file join $repo_root rtl bnn_classifier_pipelined.v] \
    [file join $repo_root fpga fpga_top.v] \
    [file join $repo_root fpga fpga_top_pipelined.v] \
    [file join $repo_root fpga bnn_benchmark.v]]
foreach name {
    weights_layerA_W.mem weights_layerA_b.mem
    weights_layerB_W.mem weights_layerB_b.mem
    tb_inputs_64.mem tb_expected_64.mem
    tb_inputs_full.mem tb_expected_full.mem
    tb_hidden_full.mem tb_score_full.mem
    tb_inputs_edge.mem tb_expected_edge.mem
    tb_hidden_edge.mem tb_score_edge.mem
} {
    lappend design_files [file join $repo_root weights $name]
}
foreach path $design_files {
    if {![file exists $path]} {error "Missing project source: $path"}
    if {[lsearch -exact [get_files -quiet -of_objects [get_filesets sources_1]] $path] < 0} {
        add_files -fileset sources_1 [list $path]
    }
}
if {[lsearch -exact [get_files -quiet -of_objects [get_filesets constrs_1]] $clock_file] < 0} {
    add_files -fileset constrs_1 [list $clock_file]
}

set sim_specs [list \
    [list sim_pr2 tb_bnn_classifier [file join $repo_root rtl tb_bnn_classifier.v] FULL_TEST {30 us}] \
    [list sim_pr3 tb_fpga_top [file join $repo_root fpga tb_fpga_top.v] {} {6 us}] \
    [list sim_pipeline tb_bnn_classifier_pipelined [file join $repo_root rtl tb_bnn_classifier_pipelined.v] FULL_TEST {30 us}] \
    [list sim_pr3_pipeline tb_fpga_top_pipelined [file join $repo_root fpga tb_fpga_top_pipelined.v] {} {6 us}] \
    [list sim_benchmark_baseline tb_bnn_benchmark [file join $repo_root fpga tb_bnn_benchmark.v] FULL_TEST {30 us}] \
    [list sim_benchmark_pipeline tb_bnn_benchmark [file join $repo_root fpga tb_bnn_benchmark.v] {FULL_TEST PIPELINED} {30 us}]]
foreach spec $sim_specs {
    lassign $spec name top tb_file defines runtime
    if {[llength [get_filesets -quiet $name]] == 0} {
        create_fileset -simset $name
    }
    if {[lsearch -exact [get_files -quiet -of_objects [get_filesets $name]] $tb_file] < 0} {
        add_files -fileset $name [list $tb_file]
    }
    set_property top $top [get_filesets $name]
    set_property verilog_define $defines [get_filesets $name]
    set_property xsim.simulate.runtime $runtime [get_filesets $name]
    update_compile_order -fileset $name
}

set_property top fpga_top_pipelined [get_filesets sources_1]
update_compile_order -fileset sources_1
puts "PR23_PROJECT: $project_file"
