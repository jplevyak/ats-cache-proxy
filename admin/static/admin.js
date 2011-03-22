$(document).ready(function() {
    $("#stop-proxy-server").click(proxy_control_callback("stop"));
    $("#start-proxy-server").click(proxy_control_callback("start"));
    $("#upload-stats-checkbox").change(
        checkbox_update_callback("upload_stats", "Uploading of statistics"));
    $("#auto-update-checkbox").change(checkbox_update_callback("auto_update",
        "Auto updating"));
    $("#update-server").change(textbox_update_callback("update_server",
        "Update server"));
    $("#stats-server").change(textbox_update_callback("stats_server",
        "Stats server"));
    $("#message").click(hide_message);
    $("#update-config").click(update_now)
    hide_advanced_sections()
});

function hide_advanced_sections() {
    $(".advanced").hide();
    $(".advanced").before(
            "<a class='show_hide_advanced' href='#'>Advanced...</a>");
    $(".show_hide_advanced").click(function(event) {
        $(event.target).next().slideToggle()
    });
}

function proxy_control_callback(action) {
    return function(event) {
        $.post("/proxy_status", { action: action },
            function(data) {
                if(data['status'] == "OK") {
                    set_proxy_state(data['state'])
                }
                show_message(data['status'] + ": " + data['message']);
            }, "json")
        event.preventDefault();
    };
}

function set_proxy_state(state) {
    $("#proxy_state").text(state);
    $("#proxy_state").removeClass().addClass("proxy_state_" + state);
}

function show_message(message) {
    $("#message").text(message).hide().fadeIn();
}

function hide_message() {
    $("#message").fadeOut();
}

function checkbox_update_callback(key, friendly_name) {
    return function(event) {
        $.post("/config_update", { key: key, value: $(this).is(':checked') },
            function(data) {
                show_message((data['status'] + ": "
                        + data['message']).replace(key, friendly_name))
            }, "json")
    };
}

function textbox_update_callback(key, friendly_name) {
    return function(event) {
        $.post("/config_update", { key: key, value: $(this).val() },
            function(data) {
                show_message((data['status'] + ": "
                        + data['message']).replace(key, friendly_name))
            }, "json")
    };
}

function update_now(event) {
    $.get("/update_now",
            function(data) {
                $('#update-output').show()
                $('#update-output-content').text(data['output']);
                show_message((data['status'] + ": " + data['message']));
                check_update_time();
            }, "json");
}

function check_update_time() {
    $.get("/last_update",
            function(data) {
                text = $("#last-updated").text();
                $("#last-updated").text(data['last_update']);
            }, "json");
}
