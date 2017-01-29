$(document).ready(function () {
    var url_base = $("meta[name='url_base']").attr("content");

    $("div#save").click(function(e){
        var change_check = false;
        if(verify_data() == false){
            return;
        }

        $this = $(this);
        $thisi = $this.children(":first");

        cat = $this.attr("cat");
        if(cat == "server"){
            data = server();
        } else if(cat == "search"){
            data = search();
        } else if(cat == "quality"){
            change_check = true;
            data = quality();
        } else if(cat == "providers"){
            data = providers();
        } else if(cat == "downloader"){
            data = downloader();
        }else if(cat == "postprocessing"){
            data = postprocessing();
        }else if(cat == "plugins"){
            data = plugins();
        }

        if(data == false){
            return
        }

        post_data = JSON.stringify(data);

        $thisi.removeClass("fa-save")
        $thisi.addClass("fa-circle faa-burst animated");

        $.post(url_base + "/ajax/save_settings", {
            "data": post_data
        })

        .done(function(r) {
            response = JSON.parse(r);
            if(response["response"] == "fail"){
                toastr.error("Unable to save settings. Check log for more information.");
            } else {
                toastr.success("Settings Saved");
            }

            $thisi.removeClass("fa-circle faa-burst animated");
            $thisi.addClass("fa-save");
        });

        e.preventDefault();
    });

    function server(){
        var data = {};
        var server = {};
        var blanks = false;
        $("#server i.checkbox").each(function(){
            server[$(this).attr("id")] = $(this).attr("value");
        });
        $("#server :input").each(function(){
            if($(this).attr("id") == "theme"){

            }
            else if($(this).val() == ""){
                blanks = true;
                highlight($(this));
            }
            server[$(this).attr("id")] = $(this).val();
        });

        if(blanks == true){
            return false;
        };

        data["Server"] = server

        return data
    }

    function search(){
        var data = {};
        var search = {};
        var blanks = false;
        $("ul#search i.checkbox").each(function(){
            search[$(this).attr("id")] = $(this).attr("value");
        })
        $("ul#search :input").each(function(){
            $this = $(this);

            if($this.val() == "" && $this.attr("id") != "imdbrss"){
                blanks = true;
                highlight($this);
            }
            search[$this.attr("id")] = $this.val();
        });
        if(blanks == true){
            return false;
        };

        data["Search"] = search;
        return data
    }

    function quality(){
        var data = {};
        var quality = {};
        var blanks = false;
        var names = [];

        $("ul.quality_profile").each(function(){
            var $this = $(this);
            var tmp = {};
            var name = $this.find("li.name input.name").val();

            if(name === undefined){
                name = "Default"
            }

            if(name == "" || name === undefined){
                blanks = true;
                toastr.warning("Please enter a name for each profile.");
                return false;
            }

            if(names.includes(name)){
                blanks = true;
                toastr.warning("Please enter a unique name for each profile.");
                return false;
            }

            names.push(name);

            quality[name] = {};

            var q_list = [];
            $this.find("ul#resolution i.checkbox").each(function(){
                $_this = $(this);
                res = $_this.attr("id");
                enabled = $_this.attr("value");
                quality[name][res] = [enabled];
            });

            // order of resolutions
            var arr = $this.find("ul#resolution").sortable("toArray");
            arr.shift();
            $.each(arr, function(value, res){
                quality[name][res].push(value)
            });

            // min/max sizes
            $this.find("#resolution_size :input").each(function(){
                $_this = $(this);
                if($_this.val() == ""){
                    blanks = true;
                    highlight($_this);
                }
                res = $_this.attr("id");
                size = $_this.val();
                quality[name][res].push(size);
            })

            // word lists
            $this.find("ul#filters li input").each(function(){
                $_this = $(this);
                id = $_this.attr("id");
                value = $_this.val();
                quality[name][id] = value;
            })

            quality[name] = JSON.stringify(quality[name]);

        })

        if(blanks == true){
            return false;
        };

        $("ul#quality i.checkbox").each(function(){
            $this = $(this)
            quality[$this.attr("id")] = $this.attr("value");
        })


        data["Quality"] = quality
        return data;
    }

    function providers(){
        // The order of these tend to get jumbled. I think it sorts alphabetically, but
        // I haven't put much effort into it yet because it really doesn't affect usage.
        var data = {};
        var ind = 1;
        var cancel = false;

        newznab_indexers = {};
        $("#newznab_list li").each(function(){
            $this = $(this);
            if ($this.attr("class") == "newznab_indexer"){
                var check = $this.children("i.newznab_check").attr("value");
                var url = $this.children("input.newznab_url").val();
                var api = $this.children("input.newznab_api").val();

                // check if one field is blank and both are not blank
                if ( (url == "" || api == "") && (url + api !=="") ){
                    toastr.warning("Please complete or clear out incomplete providers.");
                    newznab_indexers = {}
                    cancel = true;
                }

                // but ignore it if both are blank
                else if (url + api !=="") {
                    newznab_indexers[ind] = [url, api, check].toString().toLowerCase();
                    ind++;
                }
            }
        });
        data["Indexers"] = newznab_indexers;

        potato_indexers = {};
        ind = 1;
        $("#potato_list li").each(function(){
            $this = $(this);
            if ($this.attr("class") == "potato_indexer"){
                var check = $this.children("i.potato_check").attr("value");
                var url = $this.children("input.potato_url").val();
                var api = $this.children("input.potato_api").val();

                // check if one field is blank and both are not blank
                if ( (url == "" || api == "") && (url + api !=="") ){
                    toastr.warning("Please complete or clear out incomplete providers.");
                    potato_indexers = {}
                    cancel = true;
                }

                // but ignore it if both are blank
                else if (url + api !=="") {
                    potato_indexers[ind] = [url, api, check].toString().toLowerCase();
                    ind++;
                }
            }
        });
        data["PotatoIndexers"] = potato_indexers;

        torrent_indexers = {}
        $("#torrentindexer_list li").each(function(){
            $this = $(this);
            if ($this.attr("class") == "torrent_indexer"){
                name = $this.attr("id");
                check = $this.children("i.torrent_check").attr("value")
                torrent_indexers[name] = check;
            }
        });
        data["TorrentIndexers"] = torrent_indexers;
        if(cancel == true){
            return false;
        } else {
            return data
        };
    }

    function downloader(){
        var data = {};

        var sources = {};
        sources["usenetenabled"] = $("i#usenetenabled").attr("value");
        sources["torrentenabled"] = $("i#torrentenabled").attr("value");
        data["Sources"] = sources;

        var sabnzbd = {};
        sabnzbd["sabenabled"] = $("i#sabenabled").attr("value");
        $("ul#sabnzbd li input").each(function(){
            sabnzbd[$(this).attr("id")] = $(this).val();
        });
        $("ul#sabnzbd li select").each(function(){
            sabnzbd[$(this).attr("id")] = $(this).val();
        });
        data["Sabnzbd"] = sabnzbd;

        var nzbget = {};
        nzbget["nzbgenabled"] = $("i#nzbgenabled").attr("value");
        $("ul#nzbget li i.checkbox").each(function(){
            nzbget[$(this).attr("id")] = $(this).attr("value");
        });
        $("ul#nzbget li input").not("[type=button]").each(function(){
            nzbget[$(this).attr("id")] = $(this).val();
        });
        $("ul#nzbget li select").each(function(){
            nzbget[$(this).attr("id")] = $(this).val()
        });
        data["NzbGet"] = nzbget;

        var transmission = {};
        transmission["transmissionenabled"] = $("i#transmissionenabled").attr("value");
        $("ul#transmission li i.checkbox").each(function(){
            transmission[$(this).attr("id")] = $(this).attr("value");
        });
        $("ul#transmission li input").not("[type=button]").each(function(){
            transmission[$(this).attr("id")] = $(this).val();
        });
        $("ul#transmission li select").each(function(){
            transmission[$(this).attr("id")] = $(this).val()
        });
        data["Transmission"] = transmission;

        var delugerpc = {};
        delugerpc["delugerpcenabled"] = $("i#delugerpcenabled").attr("value");
        $("ul#delugerpc li i.checkbox").each(function(){
            delugerpc[$(this).attr("id")] = $(this).attr("value");
        });
        $("ul#delugerpc li input").not("[type=button]").each(function(){
            delugerpc[$(this).attr("id")] = $(this).val();
        });
        $("ul#delugerpc li select").each(function(){
            delugerpc[$(this).attr("id")] = $(this).val()
        });
        data["DelugeRPC"] = delugerpc;

        var delugeweb = {};
        delugeweb["delugewebenabled"] = $("i#delugewebenabled").attr("value");
        $("ul#delugeweb li i.checkbox").each(function(){
            delugeweb[$(this).attr("id")] = $(this).attr("value");
        });
        $("ul#delugeweb li input").not("[type=button]").each(function(){
            delugeweb[$(this).attr("id")] = $(this).val();
        });
        $("ul#delugeweb li select").each(function(){
            delugeweb[$(this).attr("id")] = $(this).val()
        });
        data["DelugeWeb"] = delugeweb;

        var qbittorrent = {};
        qbittorrent["qbittorrentenabled"] = $("i#qbittorrentenabled").attr("value");
        $("ul#qbittorrent li i.checkbox").each(function(){
            qbittorrent[$(this).attr("id")] = $(this).attr("value");
        });
        $("ul#qbittorrent li input").not("[type=button]").each(function(){
            qbittorrent[$(this).attr("id")] = $(this).val();
        });
        $("ul#qbittorrent li select").each(function(){
            qbittorrent[$(this).attr("id")] = $(this).val()
        });
        data["QBittorrent"] = qbittorrent;

        return data
    }

    function postprocessing(){
        var data = {};
        var postprocessing = {};
        $("ul#postprocessing li i.checkbox").each(function(){
            postprocessing[$(this).attr("id")] = $(this).attr("value");
        });
        $("ul#postprocessing li input").not("[type=button]").each(function(){
            $this = $(this);
            if($this.attr("id") == "moveextensions"){
                postprocessing["moveextensions"] = $this.val().split(", ").join(",");
            } else {
            postprocessing[$this.attr("id")] = $this.val();
            }
        });

        data["Postprocessing"] = postprocessing;

        return data
    }

    function plugins(){
        var data = {};
        var plugins = {};

        var added = {};
        var arr = $("ul#added").sortable("toArray");
        var order = 0
        $.each(arr, function(index, value){
            $li = $("li#" + value);
            plugin = $li.attr("plugin");
            enabled = $li.find("i.checkbox").attr("value");
            if(enabled == 'true'){
                added[plugin] = [enabled, order];
                order++;
            }
        })
        plugins["added"] = JSON.stringify(added)

        var snatched = {};
        var arr = $("ul#snatched").sortable("toArray");
        var order = 0
        $.each(arr, function(index, value){
            console.log(order)
            $li = $("li#" + value);
            plugin = $li.attr("plugin");
            enabled = $li.find("i.checkbox").attr("value");
            if(enabled == 'true'){
                snatched[plugin] = [enabled, order];
                order++;
            }
        })
        plugins["snatched"] = JSON.stringify(snatched)

        var finished = {};
        var arr = $("ul#finished").sortable("toArray");
        var order = 0;
        $.each(arr, function(index, value){
            $li = $("li#" + value);
            plugin = $li.attr("plugin");
            enabled = $li.find("i.checkbox").attr("value");
            if(enabled == 'true'){
                finished[plugin] = [enabled, order];
                order++;
            }
        })
        plugins["finished"] = JSON.stringify(finished)

        data["Plugins"] = plugins;

        return data
    }

    function verify_data(){

        //check if only one downloader is active:
        var enabled = 0
        $("ul#downloader > li > i.checkbox").each(function(){
            if($(this).attr("value") == "true"){
                enabled++;
            }
        });

        if(enabled > 1){
            toastr.warning("Please enable only one downloader.")
            return false
        }
        return true
    }

    function highlight(element){
        orig_bg = element.css("background-color");
        element.css("background-color", "#f4693b");
        element.delay(500).animate({"background-color": orig_bg}, 1000);
    }

});
