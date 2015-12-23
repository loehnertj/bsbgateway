function submit_field_null(elem) {
    return submit_field(elem, {});
}

function submit_field_choice(elem) {
    return submit_field(
        elem,
        { value:$(elem).children('select[name="value"]').val() }
    );
}

function submit_field_time(elem) {
    return submit_field(
        elem,
        { 
            hour:$(elem).children('input[name="hour"]').val(),   
            minute:$(elem).children('input[name="minute"]').val()   
        }
    );
}

function submit_field_int8(elem) {
    return submit_field(
        elem,
        { value:$(elem).children('input[name="value"]').val() }
    );
}
function submit_field_int16(elem) {
    return submit_field(
        elem,
        { value:$(elem).children('input[name="value"]').val() }
    );
}
function submit_field_temperature(elem) {
    return submit_field(
        elem,
        { value:$(elem).children('input[name="value"]').val() }
    );
}

function submit_field(elem, data) {
    var url = $(elem).attr('action');
    var id = url.replace('field-', '');
    $.ajax(url, {
        type: 'POST',
        data: data,
        dataType: 'text',
        error: function (response, textStatus, errorThrown) {
            $('#fieldsetresult-'+id).text(textStatus+' '+errorThrown + ' ' + response.responseText).addClass('error');
        },
        success: function (result) {
            $('#fieldsetresult-'+id).text(result).toggleClass('error', (result!='OK'));
            if (result=='OK') {
                $('#fieldwidget-'+id).load('field-'+id+'.widget');
            }
        }
    });
    return false;
}