function save_score(input) {
    input = $(input);
    var alias = input.attr("id").split("__", 1)[0]
    var assignment = input.attr("id").substring(alias.length + 2);
    var value = input.val();
    if (input.hasClass("percent_type")) {
        if (value !== "None" && !value.endsWith("%")) {
            value = value + "%";
        }
    }
    var data = {
        "alias": alias,
        "assignment": assignment,
        "value": value
    };
    $.post("/save_score", JSON.stringify(data))
        .done(function(response) {
            response = JSON.parse(response);
            for (var i = 0; i < response.length; i++) {
                var id = "#" + response[i][0];
                $(id).val(response[i][1]);
            }
        })
        .fail(function () {
            console.log("failed");
        });
}
