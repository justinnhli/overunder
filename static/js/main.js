var SAVING = {};
var FAILED = {};

function focus_cell(input) {
    input = $(input);
    input.parent().css("border", "1px double #2185D0");
    input.css("box-shadow", "inset 0 -100px 0 rgba(33,133,208,.15)");
}

function blur_cell(input) {
    input = $(input);
    input.parent().css("border", "1px solid #ECECEC");
    input.css("box-shadow", "");
    update_score(input);
}

function update_score(input) {
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
    if (!(input_id in SAVING) || isNaN(SAVING[input_id]) || (input_id in FAILED)) {
        SAVING[input_id] = 0;
    }
    SAVING[input_id] += 1;
    input.parent().addClass("parsing");
    $.post("/update_score", JSON.stringify(data))
        .done(function (response) {
            response = JSON.parse(response);
            for (var i = 0; i < response.length; i++) {
                $("#" + response[i][0]).html(response[i][1]);
            }
            SAVING[input_id] -= 1;
            if (SAVING[input_id] === 0) {
                delete SAVING[input_id];
                delete FAILED[input_id];
                input.parent().removeClass("parsing");
            }
        })
        .fail(function () {
            FAILED[input_id] = true;
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
    var expander = $("#" + qualified_name + "-expander");
    if (expander.html() === "-") {
        expander.html("+");
        $("." + qualified_name).hide();
    } else {
        expander.html("-");
        $("." + qualified_name).show();
    }
}
