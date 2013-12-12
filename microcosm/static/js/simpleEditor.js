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

      this.textarea = this.$el.find('textarea')[0];

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
      var output = this.insertLinkWith("!(%s)[%s]");
      if (output){
        this.textarea.value = output;
      }
    };

    simpleEditor.prototype.image = function(){

      var output = this.insertLinkWith("!(%s)[%s]");
      if (output){
        this.textarea.value = output;
      }
    };

    simpleEditor.prototype.calcTextareaHeight = function(e){
      var _this = e.currentTarget;
      _this.style.minHeight = _this.scrollHeight + 'px';
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
        ['keyup',    'textarea',    'calcTextareaHeight']
      ];

      for(var i in events){
        this.$el.on(events[i][0], events[i][1], $.proxy(this[events[i][2]], this) );
      }

    };

    return simpleEditor;
  })();

})(window,document,jQuery);