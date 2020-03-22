function save_score(input) {
    input = $(input);
    var alias = input.attr("id").split("__", 1)[0];
    var assignment = input.attr("id").substring(alias.length + 2);
    var value = input.val();
    var data = {
        "alias": alias,
        "assignment": assignment,
        "value": value
    };
    $.post("/save_score", JSON.stringify(data))
        .done(function (response) {
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

function create_child(qualified_name) {
    var assignment_name = prompt("What is the name of the assignment?");
    var weight_str = prompt("What is the weight of the assignment?");
    var data = {
        "qualified_name": qualified_name + "__" + assignment_name,
        "weight_str": weight_str
    };
    $.post("/create-child", JSON.stringify(data))
        .done(function (response) {
            location.reload();
        });
    return false;
}

function toggle_descendants(qualified_name) {
    $("." + qualified_name).toggle();
    var expander = $("#" + qualified_name + "-expander");
    if (expander.html() === "-") {
        expander.html("+");
    } else {
        expander.html("-");
    }
}
