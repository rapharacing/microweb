(function(w,d,$,undefined){
  'use strict';

  var Subscribe = (function(){

    var subscribe = function(opts){
      this.el = false;
      if (opts.el){
        this.el     = document.querySelectorAll(opts.el);
        this.$el    = $(this.el);
        this.button = this.$el.find('button');
        this.meta   = this.$el.find('.subscribe-meta');
        this.meta.hide();
      }
      this.bind();
    };

    subscribe.prototype.toggleMeta = function(){
      this.meta.toggle();
    };

    subscribe.prototype.activate = function(){

      this.$el.addClass('active');
      this.button.addClass('btn-success').find('strong').html("Added to updates");
      this.meta.slideDown();
    };

    subscribe.prototype.deactivate = function(){
      this.$el.removeClass('active');
      this.button.removeClass('btn-success').find('strong').html('Subscribe');
      this.meta.slideUp();
    };

    subscribe.prototype.toggle = function(){

      if(this.$el.hasClass('active')){
        this.deactivate();
      }else{
        this.activate();
      }
    };

    subscribe.prototype.bind = function(){

      // only binds for elements inside this.$el.display
      var events = [
        ['click', 'button', 'toggle']
      ];

      for(var i in events){
        this.$el.on(events[i][0], events[i][1], $.proxy(this[events[i][2]], this) );
      }

    };

    return subscribe;

  })();

  var s = new Subscribe({
    el : '.subscribe'
  });


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
    if (metabar[0].style.left === '0px'){
      metabar.css('left','100%');
    }else{
      metabar.css('left','0');
    }
  });

})();