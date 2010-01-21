package es.deusto.weblab.client.ui.widgets;

import com.google.gwt.event.dom.client.KeyCodes;
import com.google.gwt.event.dom.client.KeyPressEvent;
import com.google.gwt.event.dom.client.KeyPressHandler;
import com.google.gwt.user.client.ui.HorizontalPanel;
import com.google.gwt.user.client.ui.TextBox;
import com.google.gwt.user.client.ui.Widget;

public class WlTextBoxWithButton implements IWlWidget{

	private final TextBox textbox;
	private final WlButton sendButton;
	private final Widget widget;
	private final WlActionListenerContainer actionListenerContainer;
	
	private static final int DEFAULT_LENGTH      = 10;
	private static final int BUTTON_MILLISECONDS = 500;
	
	public WlTextBoxWithButton(){
		this(WlTextBoxWithButton.DEFAULT_LENGTH);
	}
	
	public WlTextBoxWithButton(int length){
		this.actionListenerContainer = new WlActionListenerContainer();
		
		this.textbox = new TextBox();
		this.textbox.setWidth(length + "em");
		
		final KeyPressHandler keyboardHandler = new KeyPressHandler(){
			public void onKeyPress(KeyPressEvent event) {
				if(event.getCharCode() == KeyCodes.KEY_ENTER){
					WlTextBoxWithButton.this.fireEnterKey();
				}
			}
		};
		this.textbox.addKeyPressHandler(keyboardHandler);
		
		this.sendButton = new WlButton(WlTextBoxWithButton.BUTTON_MILLISECONDS);
		this.sendButton.addActionListener(new IWlActionListener(){
			public void onAction(IWlWidget widget) {
				WlTextBoxWithButton.this.fireActionListener();
			}
		});
		
		final HorizontalPanel hpanel = new HorizontalPanel();
		hpanel.add(this.textbox);
		hpanel.add(this.sendButton.getWidget());
		
		this.widget = hpanel;		
	}

	public String getText(){
		return this.textbox.getText();
	}
	
	public void addActionListener(IWlActionListener listener){
		this.actionListenerContainer.addActionListener(listener);
	}

	public void removeActionListener(IWlActionListener listener){
		this.actionListenerContainer.removeActionListener(listener);
	}
	
	private void fireEnterKey(){
		this.sendButton.buttonPressed();
		this.fireActionListener();
	}
	
	private void fireActionListener(){
		this.actionListenerContainer.fireActionListeners(this);
	}

	@Override
	public Widget getWidget() {
		return this.widget;
	}

	public void dispose() {
	}
}
