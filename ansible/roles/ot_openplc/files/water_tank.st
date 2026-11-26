(*
  OT-ICS Lab - Water tank level control
  ------------------------------------------------------------------
  Modbus map (OpenPLC v3 addressing):
    Coil 0  %QX0.0  pump_cmd     inlet pump (PLC-driven in AUTO)
    Coil 1  %QX0.1  drain_valve  operator-controlled drain
    Coil 2  %QX0.2  mode_auto    TRUE = PLC controls pump
    Coil 3  %QX0.3  high_alarm   level >= 950
    Coil 4  %QX0.4  low_alarm    level <= 50
    HR 1024 %MW0    tank_level   0-1000 (0.0-100.0 %), written by field I/O sim
    HR 1025 %MW1    hi_setpoint  pump stops at/above this level
    HR 1026 %MW2    lo_setpoint  pump starts at/below this level
*)
PROGRAM WaterTank
  VAR
    pump_cmd    AT %QX0.0 : BOOL;
    drain_valve AT %QX0.1 : BOOL;
    mode_auto   AT %QX0.2 : BOOL;
    high_alarm  AT %QX0.3 : BOOL;
    low_alarm   AT %QX0.4 : BOOL;
    tank_level  AT %MW0 : UINT;
    hi_setpoint AT %MW1 : UINT;
    lo_setpoint AT %MW2 : UINT;
  END_VAR
  VAR
    initialized : BOOL := FALSE;
  END_VAR

  (* First scan: load safe defaults *)
  IF NOT initialized THEN
    mode_auto := TRUE;
    initialized := TRUE;
  END_IF;
  IF hi_setpoint = 0 THEN
    hi_setpoint := 800;
  END_IF;
  IF lo_setpoint = 0 THEN
    lo_setpoint := 200;
  END_IF;

  (* Hysteresis control *)
  IF mode_auto THEN
    IF tank_level <= lo_setpoint THEN
      pump_cmd := TRUE;
    END_IF;
    IF tank_level >= hi_setpoint THEN
      pump_cmd := FALSE;
    END_IF;
  END_IF;

  high_alarm := tank_level >= 950;
  low_alarm := tank_level <= 50;
END_PROGRAM


CONFIGURATION Config0
  RESOURCE Res0 ON PLC
    TASK task0(INTERVAL := T#100ms, PRIORITY := 0);
    PROGRAM instance0 WITH task0 : WaterTank;
  END_RESOURCE
END_CONFIGURATION
