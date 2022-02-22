{{% meta_info info_type="title" %}}${head["title"]}{{% /meta_info %}}
{{% meta_info info_type="title" %}}${head["byline"]}{{% /meta_info %}}
<%
    container = ["src-flex-container", "src-flex-container-rev"]
    flip = 0
%>
% for entry in body:
    <div class="${container[flip]}">
<%
    flip = 1 - flip
%>
        <div class="src-flex-item">
        {{% singlepic image="${entry['picture']}" width="400px" height="300px" alignment="center" caption="" title=""  \
            has_borders="False" %}}
        </div>
        <div class="src-flex-item">
            %for item in entry['text']:
                ${item}
            %endfor
        </div>
    </div>
% endfor
