{{% meta_info info_type="title" %}}${head["title"]}{{% /meta_info %}}
<div>Maintained by: ${head["byline"]}</div>
<div style="font-size: smaller; font-weight: bolder;margin-left: 30px; margin-bottom: 15px">Last
    updated: ${head["updated"]}</div>
% for para in head["header_text"].split('\\n'):
    <p>${para}</p>
% endfor
<% buttons = [x for x in body if 'button' in x.keys()] %>
% if len(buttons) > 0:
    <div class="container" style="display: flex">
        % for button_entry in buttons:
            <figure class="src_picker" style="width: 200px" data-group="${button_entry['group']}">
                <img src="${button_entry['picture']}" height="80px"/>
                <figcaption>${button_entry['caption']}</figcaption>
            </figure>
        % endfor
    </div>
% endif

## Beware of allowing the opening div to indent 4 spaces - causes Markdown code insert
<% club_entries = len([ x for x in body if 'type' in x.keys() and x['type']=='club']) %>
% if club_entries > 0:
    <div class="container">
        <h2>Campus Clubs and Informal Groups</h2>
        % for entry in body:
            % if 'group' in entry.keys():
                <%
                    eg = entry['group']
                %>
            % else:
                <%
                    eg = ''
                %>
            % endif
            % if  'type' in entry.keys() and entry['type'] == 'club':
                <div class="src-flex-item src_select_content_el" data-group="${eg}">
                    <h3>${entry['name']}</h3>
                    <div>Contact: ${entry['contact']} (${entry['phone']})</div>
                    <div>Meeting Schedule: ${entry['schedule']}</div>
                    <div>Meeting Location: ${entry['location']}</div>
                    %if entry['URL'] and entry['URL'] != '':
                        <div>URL: <a href="${entry['URL']}">Visit ${entry['name']}</a></div>
                    %endif
                    <div style="font-size: smaller; margin-left: 20px;">Last updated: ${entry['updated']}</div>
                </div>
            % endif
        % endfor
    </div>
% endif

<% club_entries = len([ x for x in body if 'type' in x.keys() and x['type']=='on campus']) %>
% if club_entries > 0:
    <div class="container">
        <h2>On Campus Opportunities</h2>
        % for entry in body:
            % if 'group' in entry.keys():
                <%
                    eg = entry['group']
                %>
            % else:
                <%
                    eg = ''
                %>
            % endif
            % if  'type' in entry.keys() and entry['type'] == 'on campus':
                <div class="src-flex-item src_select_content_el" data-group="${eg}">
                    <h3>${entry['name']}</h3>
                    <div>Contact: ${entry['contact']} (${entry['phone']})</div>
                    <div>Meeting Schedule: ${entry['schedule']}</div>
                    <div>Meeting Location: ${entry['location']}</div>
                    %if entry['URL'] and entry['URL'] != '':
                        <div>URL: <a href="${entry['URL']}">Visit ${entry['name']}</a></div>
                    %endif
                    <div style="font-size: smaller; margin-left: 20px;">Last updated: ${entry['updated']}</div>
                </div>
            % endif
        % endfor
    </div>
% endif

<% club_entries = len([ x for x in body if 'type' in x.keys() and x['type']=='off campus']) %>
% if club_entries > 0:
    <div class="container">
        <h2>Off Campus Opportunities</h2>
        % for entry in body:
            % if 'group' in entry.keys():
                <%
                    eg = entry['group']
                %>
            % else:
                <%
                    eg = ''
                %>
            % endif
            % if  'type' in entry.keys() and entry['type'] == 'off campus':
                <div class="src-flex-item src_select_content_el" data-group="${eg}">
                    <h3>${entry['name']}</h3>
                    <div>Contact: ${entry['contact']} (${entry['phone']})</div>
                    <div>Meeting Schedule: ${entry['schedule']}</div>
                    <div>Meeting Location: ${entry['location']}</div>
                    %if entry['URL'] and entry['URL'] != '':
                        <div>URL: <a href="${entry['URL']}">Visit ${entry['name']}</a></div>
                    %endif
                    <div style="font-size: smaller; margin-left: 20px;">Last updated: ${entry['updated']}</div>
                </div>
            % endif
        % endfor
    </div>
% endif
