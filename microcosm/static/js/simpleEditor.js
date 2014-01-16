(function(w,d,$,undefined){
  'use strict';

  w.simpleEditor = (function(){

    var simpleEditor = function(opts){
      this.el = false;
      if (typeof opts.el !== "undefined"){

        if (typeof opts.el == "string"){
          this.el = document.querySelector(opts.el);
          this.$el = $(this.el);
        }else{
          this.$el = opts.el;
          this.el = this.$el[0];
        }
      }

      this.no_attachments = false;
      if (typeof opts.no_attachments !== 'undefined'){
        this.no_attachments = opts.no_attachments;
      }


      this.textarea = this.$el.find('textarea')[0];

      this.form = this.$el.find('form');

      this.bind();

      return this;
    };


    simpleEditor.prototype.nothingSelected = function(){
      return this.el.selectionStart === this.el.selectionEnd;
    };

    simpleEditor.prototype.getSelectionDetailsObject = function(){


      var text           = this.textarea.value,
          startPos       = this.textarea.selectionStart,
          endPos         = this.textarea.selectionEnd,
          selectedLength = this.textarea.selectionEnd-this.textarea.selectionStart;

      var startText     = text.substr(0,startPos),
          selectedText  = text.substr(startPos,selectedLength),
          endText       = text.substr(endPos,text.length);

      var retval = {
        start     : {
          position : startPos,
          text     : startText
        },
        end       : {
          position : endPos,
          text     : endText
        },
        selected  : {
          length   : selectedLength,
          text     : selectedText
        }
      };

      return retval;

    };

    simpleEditor.prototype.applyFormatting = function(text, tag){

      // splits text into array by newlines and applies tag to each index of array.
      var selectedTextFragments = text.split(/\n/g);
      for(var i=0,j=selectedTextFragments.length;i<j;i++){
          selectedTextFragments[i] = tag.replace(/%s/g, selectedTextFragments[i]);
      }

      var formattedText = selectedTextFragments.join('\n');

      return formattedText;
    };

    simpleEditor.prototype.formattedTextWith = function(tag){

      var selection = this.getSelectionDetailsObject();

      var newText = selection.start.text +
                    this.applyFormatting(selection.selected.text, tag) +
                    selection.end.text;

      return newText;
    };

    simpleEditor.prototype.insertLinkWith = function(tag){

      var selection = this.getSelectionDetailsObject();
      var link, newText;

      if (selection.selected.length < 1){
        link = w.prompt("Paste url here:");
        if (!link){
          return false;
        }
      }else{
        link = selection.selected.text;
      }

      newText = selection.start.text +
                    this.applyFormatting(link, tag) +
                    selection.end.text;

      return newText;
    };

    simpleEditor.prototype.h1 = function(){
      this.textarea.value = this.formattedTextWith("\n%s\n====");
    };

    simpleEditor.prototype.bold = function(){
      this.textarea.value = this.formattedTextWith("**%s**");
    };

    simpleEditor.prototype.italics = function(){
      this.textarea.value = this.formattedTextWith("*%s*");
    };

    simpleEditor.prototype.list = function(){
      this.textarea.value = this.formattedTextWith("*%s");
    };

    simpleEditor.prototype.quote = function(){
      this.textarea.value = this.formattedTextWith("> %s");
    };

    simpleEditor.prototype.link = function(){
      var output = this.insertLinkWith("[%s](%s)");
      if (output){
        this.textarea.value = output;
      }
    };

    simpleEditor.prototype.image = function(){

      var output = this.insertLinkWith("![%s](%s)");
      if (output){
        this.textarea.value = output;
      }
    };

    simpleEditor.prototype.clearAttachmentGallery = function(e){
      this.$el.find('.reply-box-attachments-gallery').html("");
      this.fileHandler.clear();
    };


    simpleEditor.prototype.renderAttachmentGallery = function(files){
      var ul,li,img;

      ul = document.createElement('ul');

      if(files.length>0){
        for(var i=0,j=files.length;i<j;i++){
          img = document.createElement('img');
          img.src = files[i].data;
          li = document.createElement('li');
          li.appendChild(img);
          ul.appendChild(li);
        }
      }
      this.$el.find('.reply-box-attachments-gallery').html(ul);
    };


    simpleEditor.prototype.removeAttachmentFile = function(e){
      var self = $(e.currentTarget);
      this.fileHandler.removeFile(self.index());
    };

    simpleEditor.prototype.onKeypressHandler = function(e){
      var _this = e.currentTarget;

      if (typeof this.peopleWidget !== 'undefined'){
        if ([64,43].indexOf(e.which)>-1){
          this.peopleWidget.on = true;
          this.peopleWidget.show();
        }
      }

    };
    simpleEditor.prototype.onKeyupHandler = function(e){
      var _this = e.currentTarget;

      if (typeof this.peopleWidget !== 'undefined'){
        if ([32,13].indexOf(e.which)>-1){
          this.peopleWidget.on = false;
          this.peopleWidget.people_invited = [];
          this.peopleWidget.hide();
        }
      }
    };

    simpleEditor.prototype.bind = function(){

      // only binds for elements inside this.$el.display
      var events = [
        ['click',    '.se-h1',      'h1'],
        ['click',    '.se-bold',    'bold'],
        ['click',    '.se-italics', 'italics'],
        ['click',    '.se-quote',   'quote'],
        ['click',    '.se-link',    'link'],
        ['click',    '.se-list',    'list'],
        ['click',    '.se-image',   'image'],
        ['keypress', 'textarea',    'onKeypressHandler'],
        ['keyup',    'textarea',    'onKeyupHandler'],
        ['reset',    'form',        'clearAttachmentGallery'],

        ['click',    '.reply-box-attachments-gallery li', 'removeAttachmentFile']

      ];

      for(var i in events){
        this.$el.on(events[i][0], events[i][1], $.proxy(this[events[i][2]], this) );
      }

      // add attachments
      if (typeof FileHandler !== 'undefined' && !this.no_attachments){
        this.fileHandler = new FileHandler({
          el : this.$el.find('.reply-box-attachments')[0],
          dropzone : '.reply-box-drop-zone, .reply-box-attachments-gallery'
        });
        // this callback fires when dropped event fires and all files are collected
        this.fileHandler.onDragged($.proxy(function(files){
          this.renderAttachmentGallery(files);
        },this));

        this.fileHandler.onRemove($.proxy(function(files){
          this.renderAttachmentGallery(files);
        },this));
      }

      var subdomain = $('meta[name="subdomain"]').attr('content');
      var static_url = subdomain;
      var dataSource = subdomain + '/api/v1/profiles?disableBoiler&top=true&q=';

      if (typeof $.fn.textcomplete !== 'undefined'){

        $(this.textarea).textcomplete([
          {
            match: /\B([@+][\-+\w]*)$/,
            search: function (term, callback) {

              var _term = term.substr(1,term.length-1),
                  _symbol = term[0],
                  _callback = callback;

              $.ajax({
                url : dataSource + _term,
              }).success(function(data){

                _callback($.map(data.profiles.items, function (person) {
                    if (person.profileName.toLowerCase().indexOf(_term.toLowerCase()) === 0){
                      person.symbol = _symbol;

                      return person;
                    }else{
                      return null;
                    }
                }));
              });
            },
            template: function (person) {
                return '<img src="' + static_url + person.avatar + '" /> ' + person.symbol + person.profileName;
            },
            replace: function (person) {
                return person.symbol + person.profileName;
            },
            index: 1,
            maxCount: 5
          }
        ]);
      }
    };

    return simpleEditor;
  })();

})(window,document,jQuery);