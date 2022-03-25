{{% meta_info info_type="title" %}}${head["title"]}{{% /meta_info %}}
<%def name="base_url()">${head['base_url']}</%def>

<table class="container">
    % for entry in body:
                        <%def name="this_url()">
                    head['base_url'] + entry['url']
                </%def>
        <tr>
            <td class="src-flex-item">
                ${entry['text']}
            </td>
            <td>
                <a type="button" class="btn btn-primary is-link"
                        href="${base_url()}${entry['url']}/">${entry['button']}</a>
            </td>
        </tr>
    % endfor
</table>

<%doc>
---
title:  Resident Led Activities
base_url:       /pages/activities-index/resident-activities-index/
---
button: Clubs
url:    clubs
text:   Clubs are resident generally more formally organized groups with set activities, scheduled meetings, leadership
---
</%doc>