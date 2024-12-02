package {

    import mx.core.UIComponent;

    public class Outline extends UIComponent
    {
        override protected function updateDisplayList( 
                 unscaledWidth:Number, 
                 unscaledHeight:Number):void 
        { 
            graphics.clear()
            graphics.beginFill(0xffffff, 0);
            graphics.lineStyle(1, 0xffffff, 0.5);
            graphics.drawCircle(35, 35, 35);
            graphics.endFill();
        }
    }
}
