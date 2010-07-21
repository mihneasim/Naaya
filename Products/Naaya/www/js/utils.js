/**
 * Replaces all links with rel="external" to target="_blank"
 * This is done to ensure html strict validation
*/
function externalLinks() {
    if (!document.getElementsByTagName) return;
    var anchors = document.getElementsByTagName("a");
    for (var i=0; i<anchors.length; i++) {
        var anchor = anchors[i];
        if (anchor.getAttribute("rel") == "external") {
            anchor.target = "_blank";
            anchor.style.display = "inline";
        }
        else {
            anchor.style.display = "";
        }
    }
}
window.onload = externalLinks;

function gettext(msgid) {
    // Translates javascript strings
    if(typeof(naaya_i18n_catalog) == 'undefined') {
        return msgid;
    }
    var value = naaya_i18n_catalog[msgid];
    if (typeof(value) == 'undefined') {
       return msgid;
    } else {
       return (typeof(value) == 'string') ? value : value[0];
    }
}

/**
 *
 * Collapse Mainsection folders
 * 
*/

/**
 * Set default vars
*/
var collapse_others = false;
var default_expanded = true;

function is_folder_expanded(folderId) {
    var cookie_val = readCookie(mainsections_cookie);
    
    if (cookie_val == null) {
        return default_expanded;
    }
    
    var cookie_ob = JSON.parse(unescape(cookie_val));
    
    if (cookie_ob[folderId] == null) {
        return default_expanded;
    }
    
    return cookie_ob[folderId] == 'expanded';
}

function change_cookie_value(folderId, new_value) {
    var cookie_val = readCookie(mainsections_cookie);
    if (cookie_val == null) {
	var cookie_ob = {};
    }else {
	var cookie_ob = JSON.parse(unescape(cookie_val));
    }
    
    cookie_ob[folderId] = new_value;
    var new_cookie_val = JSON.stringify(cookie_ob)
    return createCookie(mainsections_cookie, escape(new_cookie_val), 1);
}

function expand_folder(folderId) {
    $('#img'+folderId).attr('src', img_collapse);
    $('#ul'+folderId).show();
    
    if (collapse_others) {
        $('.mainsection_title img').each(function(){
            if (this.id.substr(3) != folderId){
                collapse_folder(this.id.substr(3));
            }
        })
    }
    
    return change_cookie_value(folderId, 'expanded');
}

function collapse_folder(folderId) {
    $('#img'+folderId).attr('src', img_expand);
    $('#ul'+folderId).hide();
    return change_cookie_value(folderId, 'collapsed');
}

function toggleFolder(folderId) {
    if (is_folder_expanded(folderId)) {
        return collapse_folder(folderId);
    } else {
        return expand_folder(folderId);
    }
}

/**
 * Javascript cookies functions
 *
 * @addon     http://www.quirksmode.org/js/cookies.html
*/

function createCookie(name,value,days) {
    if (days) {
        var date = new Date();
        date.setTime(date.getTime()+(days*24*60*60*1000));
        var expires = '; expires='+date.toGMTString();
    }
    else var expires = '';
    return document.cookie = name+'='+value+expires+'; path=/';
}

function readCookie(name) {
    var nameEQ = name + '=';
    var ca = document.cookie.split(';');
    
    for(var i = 0; i < ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1,c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
    }
    
    return false;
}

function eraseCookie(name) {
    return createCookie(name,'',-1);
}

var mainFolderIds = [];
$(function() {
    for (var i = 0; i < mainFolderIds.length; i++) {
        var folderId = mainFolderIds[i];
        
        if (is_folder_expanded(folderId)) {
            expand_folder(folderId);
        } else {
            collapse_folder(folderId);
        }
    }
    
    return false;
});

/**
 * End collapse block functions
*/
