package {

    import mx.core.UIComponent;
    
    public class Circle extends UIComponent
    {
        public function set color(i:int): void {
            _color = i;
			invalidateDisplayList(); 
        }
        private var _color: int;
        override protected function updateDisplayList( 
                 unscaledWidth:Number, 
                 unscaledHeight:Number):void 
        { 
            graphics.clear()
            graphics.beginFill(_color, 0.25);
            graphics.drawCircle(35, 35, 35);
            graphics.endFill();
        }
    }
}

