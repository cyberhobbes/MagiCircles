
function handlefollow() {
    $('#follow').submit(function(e) {
	e.preventDefault();
	var loader = $('#follow-hidden-loader');
	var button = $('#follow input[type="submit"]');
	loader.width(button.width());
	button.hide();
	loader.show();
	$(this).ajaxSubmit({
	    success: function(data) {
		if (data['result'] == 'followed' || data['result'] == 'unfollowed') {
		    if (data['result'] == 'followed') {
			$('#follow input[type="hidden"]').prop('name', 'unfollow');
		    } else if (data['result'] == 'unfollowed') {
			$('#follow input[type="hidden"]').prop('name', 'follow');
		    }
		    var value = button.prop('value');
		    button.prop('value', button.attr('data-reverse'));
		    button.attr('data-reverse', value);
		}
		loader.hide();
		button.show();
		if (typeof data['total_followers'] != 'undefined') {
		    $('a[href="#followers"] strong').text(data['total_followers']);
		    if (data['total_followers'] == 0) {
			$('a[href="#followers"]').hide();
		    } else {
			$('a[href="#followers"]').show();
		    }
		}
	    },
	    error: genericAjaxError,
	});
    });

    $('a[href="#followers"]').click(function(e) {
	e.preventDefault();
	var username = $('#username').text();
	var text = $(this).closest('tr').find('th').text();
	$.get('/ajax/users/?followers_of=' + username, function(data) {
	    freeModal(username + ': ' + text, data);
	});
    });
    $('a[href="#following"]').click(function(e) {
	e.preventDefault();
	var username = $('#username').text();
	var text = $(this).closest('tr').find('th').text();
	$.get('/ajax/users/?followed_by=' +  username, function(data) {
	    freeModal(username + ': ' + text, data);
	});
    });
}

function profileTabs() {
    $('#profiletabs li a').on('show.bs.tab', function (e) {
	if ($(e.target).attr('href') == '#profileactivities' && $('#activities').text() == "") {
	    var user_id = $('#username').data('user-id');
	    $.get('/ajax/activities/?owner_id=' + user_id, function(html) {
		$('#activities').html(html);
		updateActivities();
		pagination('/ajax/activities/', '&owner_id=' + user_id, updateActivities);
	    })
	}
    });
}

$(document).ready(function() {
    handlefollow();
    applyMarkdown($('.topprofile .description'));
    profileTabs();
});
