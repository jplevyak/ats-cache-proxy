%def head():
    <script type="text/javascript" src="/static/jquery.js"></script>
    <script type="text/javascript" src="/static/admin.js"></script>
%end
%rebase base title="Index", head=head
<h1>Gproxy Admin Control Panel</h1>
<div class="section">
    <h2>Proxy Server</h2>
    <p>Proxy server state is:
        <span id="proxy_state"
        class="proxy_state_{{proxy_state}}">{{proxy_state}}</span></p>
    <p>
        <button id="stop-proxy-server">Stop Proxy</button>
        <button id="start-proxy-server">Start Proxy</button>
    </p>
</div>
<div class="section">
    <h2>Configuration/auto-updating</h2>
    <p>Last updated: <span id="last-updated">{{last_updated}}</span></p>
    <p><button id="update-config">Update now</button></p>
    <div id="update-output">
        <h3>Output from manual update</h3>
        <p class="output" id="update-output-content">No output</p>
    </div>
    <div class="advanced">
        <p><input type="checkbox" id="auto-update-checkbox"
            {{'checked="checked"' if config['auto_update'] else ''}}/>
            Enable automatic updating</p>
        <p>Server to update from: <input type="text" id="update-server"
            value="{{config['update_server']}}"/></p>
        <!--<p><a href="/config">View configuration files</a></p>-->
    </div>
</div>
<div class="section">
    <h2>Statistics</h2>
    <p><input type="checkbox" id="upload-stats-checkbox"
        {{'checked="checked"' if config['upload_stats'] else ''}}/>
        Allow uploading of anonymous proxy statistics to Google</p>
    <p><a href="/view_stats">View statistics for this client</a></p>
    <div class="advanced">
        <p>Server to upload stats to: <input type="text" id="stats-server"
            value="{{config['stats_server']}}"/></p>
    </div>
</div>

