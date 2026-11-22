
// https://www.softcatala.org/sc/v2/api/nmt-engcat
var URL='http://localhost:8700'

var HttpClient = function() {
    this.get = function(aUrl, aCallback) {
        var anHttpRequest = new XMLHttpRequest();
        anHttpRequest.onreadystatechange = function() { 
            if (anHttpRequest.readyState == 4 && anHttpRequest.status == 200)
                aCallback(anHttpRequest.responseText);
        }

        anHttpRequest.open( "GET", aUrl, true );
        anHttpRequest.send( null );
    }
}

// Fill both language-pair selects from the pairs the service actually has loaded.
function load_pairs() {
    var client = new HttpClient();
    client.get(URL + '/listPairs', function(response) {
        var pairs = JSON.parse(response)['responseData'];
        var codes = [...new Set(pairs.flatMap(p => [p.sourceLanguage, p.targetLanguage]))];

        client.get(URL + '/listLanguageNames?locale=ca&languages=' + codes.join('+'), function(response) {
            var names = JSON.parse(response);
            var name = code => names[code] || code;

            pairs.forEach(function(p) {
                var label = name(p.sourceLanguage) + ' - ' + name(p.targetLanguage);
                document.getElementById('languages').add(new Option(label, p.sourceLanguage + '|' + p.targetLanguage));
                document.getElementById('model_name').add(new Option(label, p.sourceLanguage + '-' + p.targetLanguage));
            });
        });
    });
}

window.addEventListener('DOMContentLoaded', load_pairs);

function show_version() {
    url = URL + `/version/`;

    var client = new HttpClient();
    client.get(url, function(response) {
        json = JSON.parse(response);

        element = document.getElementById('version');
        var text = JSON.stringify(json);
        element.innerText = text;
    });
}

function translate_text() {

    text = document.getElementById('source_text').value;
    languages = document.getElementById('languages').value;

    var xhr = new XMLHttpRequest();
    url = URL + `/translate/`;
    xhr.open('POST', url);

    xhr.onreadystatechange = function() {
        if (xhr.readyState == XMLHttpRequest.DONE) {
            json = JSON.parse(xhr.responseText);
            element = document.getElementById('translated_text');
            text = json["responseData"]["translatedText"];
            element.value = text;

            element = document.getElementById('time_used');
            text = json["time"];
            element.innerText = text;

            element = document.getElementById('message');
            text = json["message"];
            if (typeof text == 'undefined') text = ""
            element.innerText = text;

        }
    }

    var payload = new FormData();
    payload.append('langpair', languages);
    payload.append('q', text);
    xhr.send(payload);
}


function sendFile()
{
    var xmlHttp = new XMLHttpRequest();
        xmlHttp.onreadystatechange = function()
        {
            if(xmlHttp.readyState != 4)
            {
                return;
            }

            if (xmlHttp.status == 200)
            {
                alert("D'aquí a una estona rebreu el fitxer traduït per correu electrònic");
            }
            else if (xmlHttp.status == 0)
            {
                // Connection dropped, e.g. the server rejected an oversized upload before reading it
                alert("No s'ha pogut enviar el fitxer");
            }
            else
            {
                json = JSON.parse(xmlHttp.responseText);
                alert(json['explanation'] || json['error']);
            }
        }

        // Same limit as the server (MAX_UPLOAD_BYTES); checked here because browsers may not
        // show the server's 413 if it closes the connection mid-upload.
        var file = document.querySelector('#form-id input[type=file]').files[0];
        if (file && file.size > 8 * 1024 * 1024)
        {
            alert("El fitxer és massa gran (màxim 8 MB)");
            return;
        }

        var formData = new FormData(document.getElementById('form-id'));
        url = URL + `/translate_file/`;
        xmlHttp.open("post", url);
        xmlHttp.send(formData); 
}
