var SAVING = {};

function save_score(input) {
    input = $(input);
    var input_id = input.attr("id");
    var alias = input_id.split("__", 1)[0];
    var assignment = input_id.substring(alias.length + 2);
    var value = input.val();
    var data = {
        "alias": alias,
        "assignment": assignment,
        "value": value
    };
    if (!(input_id in SAVING)) {
        SAVING[input_id] = 0;
    }
    SAVING[input_id] += 1;
    input.css("background-color", "#E08080");
    $.post("/save_score", JSON.stringify(data))
        .done(function (response) {
            response = JSON.parse(response);
            for (var i = 0; i < response.length; i++) {
                $("#" + response[i][0]).val(response[i][1]);
            }
            SAVING[input_id] -= 1;
            if (SAVING[input_id] === 0) {
                delete SAVING[input_id];
                input.css("background-color", "transparent");
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
