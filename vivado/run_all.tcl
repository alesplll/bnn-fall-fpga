# Rebuild and verify PR2, PR3 and the controlled pipeline comparison.
# Run in Vivado 2022.2: cd D:/neuroproc/bnn-fall-fpga ; source vivado/run_all.tcl
set repo_root [file normalize [file join [file dirname [info script]] ..]]
source [file join $repo_root vivado create_project.tcl]
set project_dir [file join $repo_root vivado_pr23]
set results_dir [file join $project_dir results]
set clock_file [file join $project_dir clock_run.xdc]
file mkdir $results_dir

proc assert_pass {simset mode marker} {
    global project_dir results_dir
    catch {close_sim}
    if {$mode eq "behavioral"} {
        launch_simulation -simset $simset -mode behavioral
        set phase behav
    } else {
        launch_simulation -simset $simset -mode post-synthesis -type functional
        set phase [file join synth func]
    }
    catch {close_sim}
    set log_file [file join $project_dir bnn_pr23.sim $simset $phase xsim simulate.log]
    if {![file exists $log_file]} {
        error "Simulation log not found: $log_file"
    }
    set fd [open $log_file r]
    set log_text [read $fd]
    close $fd
    if {[string first $marker $log_text] < 0 || [string first "FAIL:" $log_text] >= 0} {
        error "Simulation did not pass: $simset ($mode); see $log_file"
    }
    set sim_results [file join $results_dir simulations]
    file mkdir $sim_results
    file copy -force $log_file [file join $sim_results "${simset}_${mode}.log"]
    puts "SIM_PASS: $simset $mode"
}

proc require_mem_reads {log_file names} {
    set fd [open $log_file r]
    set log_text [read $fd]
    close $fd
    foreach name $names {
        if {[string first "data file '$name' is read successfully" $log_text] < 0} {
            error "Synthesis did not confirm reading $name; see $log_file"
        }
    }
    if {[regexp {ERROR:|CRITICAL WARNING:} $log_text]} {
        error "Synthesis log contains an error or critical warning: $log_file"
    }
}

proc build_case {case_name top period route netlist_simset} {
    global project_dir results_dir clock_file
    set out_dir [file join $results_dir $case_name]
    file mkdir $out_dir

    set fd [open $clock_file w]
    puts $fd "create_clock -name clk -period [format %.3f $period] \[get_ports clk\]"
    close $fd
    set_property top $top [get_filesets sources_1]
    update_compile_order -fileset sources_1

    # A completed old run must never be mistaken for a run of these sources.
    catch {close_sim}
    catch {close_design}
    if {![string match "*Not started*" [get_property STATUS [get_runs impl_1]]]} {
        reset_run impl_1
    }
    if {![string match "*Not started*" [get_property STATUS [get_runs synth_1]]]} {
        reset_run synth_1
    }
    launch_runs synth_1 -jobs 2
    wait_on_run synth_1
    set status [get_property STATUS [get_runs synth_1]]
    if {![string match "*Complete*" $status]} {
        error "Synthesis failed for $case_name: $status"
    }
    set synth_log [file join $project_dir bnn_pr23.runs synth_1 runme.log]
    set mem_names {weights_layerA_W.mem weights_layerA_b.mem weights_layerB_W.mem weights_layerB_b.mem}
    if {[string match "fpga_top*" $top]} {
        lappend mem_names tb_inputs_64.mem tb_expected_64.mem
    }
    require_mem_reads $synth_log $mem_names
    file copy -force $synth_log [file join $out_dir synth.log]
    set fd [open [file join $out_dir result.txt] w]
    puts $fd "top=$top"
    puts $fd "requested_period_ns=$period"
    puts $fd "synthesis_status=$status"
    close $fd
    open_run synth_1
    report_utilization -file [file join $out_dir utilization_synth.rpt]
    write_checkpoint -force [file join $out_dir synth.dcp]
    catch {close_design}

    if {$netlist_simset ne ""} {
        set marker [expr {[string match "*pipeline*" $netlist_simset] ?
            "PASS: benchmark pipelined, 2331 vectors" :
            "PASS: benchmark baseline, 2331 vectors"}]
        assert_pass $netlist_simset post-synthesis $marker
    }
    if {!$route} {
        puts "BUILD_DONE: $case_name (synthesis)"
        return
    }

    launch_runs impl_1 -to_step route_design -jobs 2
    wait_on_run impl_1
    set status [get_property STATUS [get_runs impl_1]]
    if {![string match "*Complete*" $status]} {
        error "Implementation failed for $case_name: $status"
    }
    file copy -force [file join $project_dir bnn_pr23.runs impl_1 runme.log] \
        [file join $out_dir implementation.log]
    open_run impl_1
    set actual_period [get_property PERIOD [get_clocks clk]]
    if {abs($actual_period - $period) > 0.001} {
        error "Wrong clock period in $case_name: expected $period, got $actual_period"
    }
    report_utilization -file [file join $out_dir utilization_routed.rpt]
    report_timing_summary -file [file join $out_dir timing_routed.rpt]
    report_timing -max_paths 10 -file [file join $out_dir critical_paths.rpt]
    report_route_status -file [file join $out_dir route_status.rpt]
    report_drc -file [file join $out_dir drc_routed.rpt]
    write_checkpoint -force [file join $out_dir routed.dcp]
    set worst [get_timing_paths -max_paths 1]
    if {[llength $worst] == 0} {error "No timed path in $case_name"}
    set slack [get_property SLACK $worst]
    set fd [open [file join $out_dir result.txt] a]
    puts $fd "implementation_status=$status"
    puts $fd "actual_period_ns=$actual_period"
    puts $fd "worst_setup_slack_ns=$slack"
    close $fd
    if {$slack < 0} {
        puts "TIMING_NOT_MET: $case_name period=$actual_period WNS=$slack"
    }
    puts "BUILD_DONE: $case_name period=$actual_period WNS=$slack"
}

# Behavioral checks use the same six simulation sets in this one project.
assert_pass sim_pr2 behavioral "PASS: 2331 vectors"
assert_pass sim_pipeline behavioral "PASS: pipelined classifier, 2331 vectors"
assert_pass sim_pr3 behavioral "PASS: FPGA prototype self-test"
assert_pass sim_pr3_pipeline behavioral "PASS: pipelined prototype"
assert_pass sim_benchmark_baseline behavioral "PASS: benchmark baseline, 2331 vectors"
assert_pass sim_benchmark_pipeline behavioral "PASS: benchmark pipelined, 2331 vectors"

build_case pr2_classifier bnn_classifier 20.0 0 ""
build_case baseline_20 bnn_benchmark_baseline 20.0 1 sim_benchmark_baseline
build_case pipeline_20 bnn_benchmark_pipelined 20.0 1 sim_benchmark_pipeline
build_case baseline_10 bnn_benchmark_baseline 10.0 1 ""
build_case pipeline_10 bnn_benchmark_pipelined 10.0 1 ""
build_case pr3_prototype_20 fpga_top 20.0 1 ""
build_case pr3_pipeline_20 fpga_top_pipelined 20.0 1 ""

puts "PR23_DONE: all behavioral checks, netlist checks and routed reports saved in $results_dir"
