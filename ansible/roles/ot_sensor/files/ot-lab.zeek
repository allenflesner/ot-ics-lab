##! OT-ICS lab detections. Raised through the Notice framework -> notice.log
##! -> Elastic (zeek.notice). Tune the allow-lists in otlab-site.zeek.

@load base/protocols/modbus
@load base/frameworks/notice

module OTLab;

export {
    redef enum Notice::Type += {
        ## A Modbus write function from a host not in authorized_writers. ATT&CK-ICS T0855
        Unauthorized_Modbus_Write,
        ## A Modbus client not in known_modbus_clients. ATT&CK-ICS T0846 / T0888
        Unknown_Modbus_Client,
        ## Device identification / diagnostics functions (recon). ATT&CK-ICS T0888
        Modbus_Recon_Function,
        ## A connection into the control network from outside the allowed conduits. Purdue violation
        Control_Zone_Conduit_Violation,
    };

    const authorized_writers: set[addr] = {} &redef;
    const known_modbus_clients: set[addr] = {} &redef;
    const control_net: subnet = 0.0.0.0/32 &redef;
    const conduit_sources: set[subnet] = {} &redef;

    ## FC 5/6/15/16 writes, 22 mask write, 23 read/write multiple
    const write_functions: set[count] = { 5, 6, 15, 16, 22, 23 } &redef;
    ## FC 8 diagnostics, 17 report server ID, 43 encapsulated (read device ID)
    const recon_functions: set[count] = { 8, 17, 43 } &redef;
}

event modbus_message(c: connection, headers: ModbusHeaders, is_orig: bool)
    {
    if ( ! is_orig )
        return;

    local src = c$id$orig_h;
    local dst = c$id$resp_h;
    local fc = headers$function_code;

    if ( src !in known_modbus_clients )
        NOTICE([$note=Unknown_Modbus_Client, $conn=c,
                $msg=fmt("Unknown Modbus client %s -> %s (fc=%d)", src, dst, fc),
                $identifier=cat(src, dst), $suppress_for=30min]);

    if ( fc in write_functions && src !in authorized_writers )
        NOTICE([$note=Unauthorized_Modbus_Write, $conn=c,
                $msg=fmt("Modbus WRITE fc=%d from unauthorized %s to %s", fc, src, dst),
                $identifier=cat(src, dst, fc), $suppress_for=1min]);

    if ( fc in recon_functions )
        NOTICE([$note=Modbus_Recon_Function, $conn=c,
                $msg=fmt("Modbus recon/diagnostic fc=%d from %s to %s", fc, src, dst),
                $identifier=cat(src, dst, fc), $suppress_for=10min]);
    }

event connection_established(c: connection)
    {
    local src = c$id$orig_h;
    local dst = c$id$resp_h;
    if ( dst !in control_net || src in control_net )
        return;
    for ( s in conduit_sources )
        if ( src in s )
            return;
    NOTICE([$note=Control_Zone_Conduit_Violation, $conn=c,
            $msg=fmt("Connection into control zone from %s to %s:%s", src, dst, c$id$resp_p),
            $identifier=cat(src, dst, c$id$resp_p), $suppress_for=10min]);
    }
