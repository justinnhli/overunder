function save_score(input) {
    input = $(input);
    var email = input.attr("id").split("::")[0];
    var assignment = input.attr("id").substring(email.length + 2);
    var data = {
        "email": email,
        "assignment": assignment,
        "value": $(input).val()
    };
    $.post("/save_score", JSON.stringify(data))
        .done(function(response) {
            response = JSON.parse(response);
            for (var i = 0; i < response.length; i++) {
                var id = "#" + response[i][0];
                id = id.replace("@", "_").replace(/ /g, "_").replace("|", "::");
                console.log(id);
                $(id).val(response[i][1]);
            }
        })
        .fail(function () {
            console.log("failed");
        });
}
