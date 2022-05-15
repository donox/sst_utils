{{% meta_info info_type="title" %}}${head["title"]}{{% /meta_info %}}
<div>Maintained by: ${head["byline"]}</div>
<div style="font-size: smaller; font-weight: bolder;margin-left: 30px; margin-bottom: 15px">Last
    updated: ${head["updated"]}</div>
% for para in head["header_text"].split('\\n'):
<p>${para}</p>
% endfor

% if has_buttons:
<div class="container" style="display: flex">
    % for button_entry in buttons:
        <figure class="src_picker" style="width: 200px" data-group="${button_entry['group']}">
            <img src="${button_entry['picture']}" height="80px"/>
            <figcaption>${button_entry['caption']}</figcaption>
        </figure>
    % endfor
</div>
<div style="font-size: smaller; font-weight: bolder">Click to see club list</div>
% endif
<%
    # css will set anything of class src_select_content_el to display: None, expecting
    # a button to change it.
    if has_buttons:
        content_selection_class = 'src_select_content_el'
    else:
        content_selection_class = ''
%>

## Beware of allowing the opening div to indent 4 spaces - causes Markdown code insert
% if has_clubs:
<div class="container">
    % for group in clubs.keys():
        <h2 class="src-flex-item ${content_selection_class}" data-group="${group}"> ${captions[group]}</h2>

    % for entry in clubs[group]:
        <div class="src-flex-item ${content_selection_class}" data-group="${entry['group']}">
            <h3>${entry['name']}</h3>
            <div>Contact: ${entry['contact']} (${entry['phone']})</div>
            <div>Meeting Schedule: ${entry['schedule']}</div>
            <div>Meeting Location: ${entry['location']}</div>
            %if entry['URL'] and entry['URL'] != '':
                <div>URL: <a href="${entry['URL']}">Visit ${entry['name']}</a></div>
            %endif
            <div style="font-size: smaller; margin-left: 20px;">Last updated: ${entry['updated']}</div>
        </div>
    % endfor
    % endfor
</div>
% endif


% if has_on_campus:
<div class="container">
    <h2>On Campus Opportunities</h2>
    % for entry in on_campus:
        <div class="src-flex-item ${content_selection_class}">
            <h3>${entry['name']}</h3>
            <div>Contact: ${entry['contact']} (${entry['phone']})</div>
            <div>Meeting Schedule: ${entry['schedule']}</div>
            <div>Meeting Location: ${entry['location']}</div>
            %if entry['URL'] and entry['URL'] != '':
                <div>URL: <a href="${entry['URL']}">Visit ${entry['name']}</a></div>
            %endif
            <div style="font-size: smaller; margin-left: 20px;">Last updated: ${entry['updated']}</div>
        </div>
    % endfor
</div>
% endif

% if has_off_campus:
<div class="container">
    <h2>Off Campus Opportunities</h2>
    % for entry in off_campus:
        <div class="src-flex-item ${content_selection_class}">
            <h3>${entry['name']}</h3>
            <div>Contact: ${entry['contact']} (${entry['phone']})</div>
            <div>Meeting Schedule: ${entry['schedule']}</div>
            <div>Meeting Location: ${entry['location']}</div>
            %if entry['URL'] and entry['URL'] != '':
                <div>URL: <a href="${entry['URL']}">Visit ${entry['name']}</a></div>
            %endif
            <div style="font-size: smaller; margin-left: 20px;">Last updated: ${entry['updated']}</div>
        </div>
    % endfor
</div>
% endif
