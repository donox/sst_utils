{{% meta_info info_type="title" %}}${head["title"]}{{% /meta_info %}}
{{% meta_info info_type="byline" %}}${head["byline"]}{{% /meta_info %}}
<%
    container = ["src-flex-container", "src-flex-container-rev"]
    flip = 0
%>
% for entry in body:
    <div class="${container[flip]}" style="font-size: larger">
<%
    flip = 1 - flip
%>
        <div class="src-flex-item">
        {{% singlepic image="${entry['picture']}" width="400px" height="300px" alignment="center" caption="" title=""  \
            has_borders="True" %}}
        </div>
        <div class="src-flex-item">
                <p style="font-weight: bolder">${entry['speaker']}:</p>
            %for item in entry['text']:
                <p>&nbsp;&nbsp;&nbsp;&nbsp;${item}</p>
            %endfor
        </div>
    </div>
% endfor
