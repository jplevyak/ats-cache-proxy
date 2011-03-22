%def head():
    <script type="text/javascript" src="/static/jquery.js"></script>
%end
%rebase base title="Stats", head=head
<h1>Gproxy Statistics</h1>
<ul>
    <li>Average Cache Size: {{cache_size_avg}}</li>
    <li>Average Hit Rate: {{hit_rate_avg}}</li>
    <li>Latest Cache Size: {{cache_size_latest}}</li>
    <li>Latest Hit Rate: {{hit_rate_latest}}</li>
    <li>Date range for averages: {{date_from}} - {{date_to}}</li>
    <li>Date of latest values: {{date_to}}</li>
</ul>
