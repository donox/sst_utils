{{% meta_info info_type="title" %}}${head["title"]}{{% /meta_info %}}
{{% meta_info info_type="title" %}}${head["byline"]}{{% /meta_info %}}
<p>Contact any of the individuals listed below if you are interested in learning more about the Sunnyside Campus Clubs.</p>

<p>Date of most recent update is listed in [] and is dependent on each group.  Groups email Mike Bollen (wmbollen@gmail.com) with updates.</p>

<p>If you have an idea for another club/group please contact Layna Erney, IL Events Coordinator (8241).</p>
<div class="container">
    <h2>Campus Clubs and Informal Groups</h2>
    % for entry in body:
        % if  entry['type'] == 'club':
            <div class="src-flex-item">
                <h3>${entry['name']}</h3>
                <div>Contact: ${entry['contact']} (${entry['phone']})</div>
                <div>Meeting Schedule: ${entry['schedule']}</div>
                <div>Meeting Location: ${entry['location']}</div>
            </div>
        % endif
    % endfor
</div>
<div class="container">
    <h2>On Campus Opportunities</h2>
    % for entry in body:
        % if  entry['type'] == 'on campus':
            <div class="src-flex-item">
                <h3>${entry['name']}</h3>
                <div>Contact: ${entry['contact']} (${entry['phone']})</div>
                <div>Meeting Schedule: ${entry['schedule']}</div>
                <div>Meeting Location: ${entry['location']}</div>
            </div>
        % endif
    % endfor
</div>
<div class="container">
    <h2>Off Campus Opportunities</h2>
    % for entry in body:
        % if  entry['type'] == 'off campus':
            <div class="src-flex-item">
                <h3>${entry['name']}</h3>
                <div>Contact: ${entry['contact']} (${entry['phone']})</div>
                <div>Meeting Schedule: ${entry['schedule']}</div>
                <div>Meeting Location: ${entry['location']}</div>
            </div>
        % endif
    % endfor
</div>

<%doc>
type: on campus
name: Fishing Committee
updated: 3-15-22
contact: Alex Banks
phone:  8836
schedule: NA
location: NA
</%doc>