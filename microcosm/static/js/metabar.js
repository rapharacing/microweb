(function(w,d,$,undefined){
  'use strict';

  var Subscribe = (function(){

    var subscribe = function(opts){
      this.el = false;
      if (opts.el){
        this.$el    = $(opts.el);
        this.el     = this.$el[0];
        this.button = this.$el.find('.btn-switch');
        this.meta   = this.$el.find('.subscribe-meta');
        this.emailCheckbox = this.meta.find('input[name=emailme]');
      }

      this.url   = typeof opts.url !== 'undefined' ? opts.url : -1;
      this.token = typeof opts.token !== 'undefined' ? opts.token : null;

      this.data = {
        itemId    : typeof opts.id   !== 'undefined' ? opts.id   : null,
        itemType  : typeof opts.type !== 'undefined' ? opts.type : null,
        csrfmiddlewaretoken: this.token
      }

      this.is_subscribed = typeof opts.is_subscribed !== 'undefined' ? opts.is_subscribed : false;

      this.bind();
    };

    subscribe.prototype.toggleMeta = function(){
      this.meta.toggle();
    };

    subscribe.prototype.sync = function(opts){

      var request, ajaxOptions;

      ajaxOptions = {
        url  : this.url,
        type : 'POST',
        data : this.data,
        headers : {
          "X-CSRFToken" : this.token
        },
        success : $.proxy(this.onSyncSuccess,this),
        error   : $.proxy(this.onSyncError, this)
      }

      // user override
      if (typeof opts !== 'undefined'){
        if (typeof opts.data !== 'undefined'){
          ajaxOptions.data = $.extend({},this.data,opts.data)
        }
        if (typeof opts.success !== 'undefined'){
          ajaxOptions.success = opts.success;
        }
      }

      request = $.ajax(ajaxOptions);

    };

    subscribe.prototype.onSyncSuccess = function(data,status_text,xhr){

      this.is_subscribed = !this.is_subscribed;
      setTimeout($.proxy(this.render,this),500);

    };

    subscribe.prototype.onSyncError = function(data,status_text,xhr){
      setTimeout($.proxy(this.render,this),500);
    };

    subscribe.prototype.onToggleEmailCheckbox = function(){

      this.sync({
        data : {
          emailMe : this.emailCheckbox.is(':checked'),
          patch   : true
        },
        success : function(){ return 0; }
      });

    };


    subscribe.prototype.activate = function(){
      this.sync();
    };

    subscribe.prototype.deactivate = function(){
      this.sync({
        data : {
          delete : true
        }
      });
    };

    subscribe.prototype.render = function(){

      if (this.is_subscribed){
        this.$el.addClass('active');
        this.button.removeClass('loading off').addClass('on');
        this.meta.addClass('active');
      }else{
        this.$el.removeClass('active');
        this.button.removeClass('loading on').addClass('off');
        this.meta.removeClass('active');
      }
    }

    subscribe.prototype.toggle = function(){

      if (this.button.hasClass('loading')){
        return 0;
      }
      this.button.removeClass('on off').addClass('loading');
      this.meta.removeClass('active');

      if(this.is_subscribed){
        this.deactivate();
      }else{
        this.activate();
      }
    };

    subscribe.prototype.bind = function(){

      // only binds for elements inside this.$el.display
      var events = [
        ['click', '.btn-switch-on, .btn-switch-off', 'toggle'],
        ['click', 'input[name=emailme]',             'onToggleEmailCheckbox']
      ];

      for(var i in events){
        this.$el.on(events[i][0], events[i][1], $.proxy(this[events[i][2]], this) );
      }

      // disable parent form
      this.$el.on('submit','form',function(e){
        e.preventDefault();
      });

    };

    return subscribe;

  })();

  window.Subscribe = Subscribe;

})(window,document,$);

(function(w,d,$,undefined){
  'use strict';

  var Follow = (function(){

    var follow = function(opts){
      this.el = false;
      if (opts.el){
        this.el     = document.querySelectorAll(opts.el);
        this.$el    = $(this.el);
        this.button = this.$el.find('button');
      }
      this.bind();
    };

    follow.prototype.toggleMeta = function(){
      this.meta.toggle();
    };

    follow.prototype.activate = function(){

      this.$el.addClass('active');
      this.button.addClass('btn-success').html("Following");
    };

    follow.prototype.deactivate = function(){
      this.$el.removeClass('active');
      this.button.removeClass('btn-success').html('Follow');
    };

    follow.prototype.toggle = function(){

      if(this.$el.hasClass('active')){
        this.deactivate();
      }else{
        this.activate();
      }
    };

    follow.prototype.bind = function(){

      // only binds for elements inside this.$el.display
      var events = [
        ['click', 'button', 'toggle']
      ];

      for(var i in events){
        this.$el.on(events[i][0], events[i][1], $.proxy(this[events[i][2]], this) );
      }

    };

    return follow;

  })();

  var s = new Follow({
    el : '.follow'
  });


})(window,document,$);


(function(){

  $('.metabar-toggle').on('click',function(){
    var metabar = $('.metabar');
    if (metabar[0].style.right === '0px'){
      metabar[0].style.right = '-350px';
    }else{
      metabar[0].style.right = '0px';
    }
  });

})();