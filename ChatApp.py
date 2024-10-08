import pdb
import copy
import tkinter as tk
from tkinter import ttk
from tkinter import simpledialog, scrolledtext

from OpenaiHandler import openaiHandler
from AnyscaleHandler import anyscaleHandler
from AnthropicHandler import anthropicHandler
from IOFunctions import save_json_data, parse_arguments


# Dictionary mapping shorthand to proper LLM names. Change manually to test different models.
model_name_mapping = {'GPT-4': 'gpt-4o-mini', 
		'Llama3': 'meta-llama/Meta-Llama-3-70B-Instruct', 
		'Claude3': 'claude-3-haiku-20240307'}

# Dictionary mapping models to their icons
model_icons = {
	"GPT-4": ("images/gpt.png", (24, 24)),
	"Claude3": ("images/claude.png", (12, 12)),
	"Llama3": ("images/llama.png", (26, 26))
}

colors = {
	'bg_scrollable_window': '#333333',
	'user_msg_bg_dark': '#2e86c1',
	'user_msg_text_dark': '#f8f9f9',
	'user_msg_bg_light': '#85c1e9',
	'user_msg_text_light': '#17202a',
	'bot_msg_bg_dark': '#566573',
	'bot_msg_bg_light': '#eaecee',
	'edit_button_bg': '#4E6473',
}

class ChatApp:
	def __init__(self, root, config):
		self.root = root
		self.config = config
		self.chatlog = []
		self.conversations = {}
		self.msg_widgets = {}
		self.main_frame = ttk.Frame(self.root)

		# Import images
		icon_path, subsample = model_icons.get(self.config['given_model'], ("images/bot.png", (20, 20)))
		self.bot_icon = tk.PhotoImage(file=icon_path).subsample(*subsample)
		self.user_icon = tk.PhotoImage(file="images/user.png").subsample(12,12)
		self.edit_icon = tk.PhotoImage(file="images/edit.png").subsample(150,150)
		self.dots_icon = tk.PhotoImage(file="images/dots.png").subsample(8,8)

		# Draw the UI
		self.initialize_ui()

		# Bind the window close event
		self.root.protocol("WM_DELETE_WINDOW", self.on_close)

	def initialize_ui(self):
		"""
		Create all UI elements on the screen
		"""
		# Main layout of the program, giving the told name to the user
		self.root.title(f"{self.config['given_model']}")

		# Color theme button
		self.btn_color = ttk.Checkbutton(self.root, style='Switch.TCheckbutton', command=self.change_theme)
		self.btn_color.pack()

		self.botname = ttk.Label(self.root, text=f"Connected to {self.config['given_model']}", font=("Helvetica", 24, "bold"))
		self.botname.pack(pady=20)

		# Create the main canvas to draw on, create a vertical scrollbar and link it to the canvas
		self.canvas = tk.Canvas(self.main_frame, highlightthickness=0)
		self.scrollbar = ttk.Scrollbar(self.main_frame, command=self.canvas.yview)
		self.canvas.configure(yscrollcommand=self.scrollbar.set)

		# Pack the canvas to the left and set the scrollbar to the right of it
		self.canvas.pack(side='left', fill='both', expand=True)
		self.scrollbar.pack(side='right', fill='y')

		# A new frame within the canvas that is scrollable, messages will be placed in here
		self.scrollable_window = tk.Frame(self.canvas, bg=colors.get('bg_scrollable_window'))
		self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_window, anchor="nw")

		# Configure the scrollregion and bind mouse wheel to it
		self.scrollable_window.bind("<Configure>", self.update_scrollregion)
		self.canvas.bind('<Configure>', self.resize_canvas)
		self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
		self.main_frame.pack(fill='both', expand=True)

		# Bottom frame for input and send button
		bottom_frame = ttk.Frame(self.root)
		bottom_frame.pack(fill='x', padx=10, pady=5)

		# Text entry field
		self.msg_ent = ttk.Entry(bottom_frame, font=('Arial', 12))
		self.msg_ent.pack(side='left', fill='x', expand=True, padx=(22, 0), pady=10)

		# Send button
		self.btn_send = ttk.Button(bottom_frame, text="Send", style="Accent.TButton", command=self.send_message)
		self.btn_send.pack(side='right', padx=(5, 10), pady=11)
		self.root.bind('<Return>', self.send_message) # Binds enter to click send button as well

	def send_message(self, event=None):
		"""
		Handles event of user sending a message and subsequent actions once the send button is clicked
		"""
		# Get the user message from the input field and strip
		msg = self.msg_ent.get().strip()

		if msg: # Check if a blank message or not
			msg_id = len(self.chatlog) + 1 # Assign an id to the message, for logging
			msg_info = {
				'msg_id': msg_id,
				'sender': 'User',
				'content': msg
			}

			# Update the chat log, clear the input field, and draw the message to the screen
			self.chatlog.append(msg_info)
			self.msg_ent.delete(0, 'end')
			self.update_window(msg_info)

			# Draw dots to indicate the chatbot is thinking until a response is given
			self.dots_label = tk.Label(self.scrollable_window, image=self.dots_icon, bg=colors.get("bg_scrollable_window"))
			self.dots_label.pack(side='left', fill='x', padx=5)

			# This is required so that tkinter updates events properly
			self.root.after(10, self.get_llm_response)
		else:
			print("There was no message entered.")


	def edit_message(self, msg_id):
		"""
		Handles event of user editing a previous message and subsequent actions
		:param msg_id: Id number of message to edit
		"""
		# Get the message we want to edit
		msg_widget = self.msg_widgets.get(msg_id)

		# Draw the edit message elements to the screen needed for input
		edit_ent = ttk.Entry(msg_widget['frame'], font=('Arial', 14), width=25)
		edit_ent.insert(0, msg_widget['info']['content'])
		edit_ent.pack(side='right', fill='x')
		msg_widget['edit'].pack_forget()
		msg_widget['label'].pack_forget()

		# Create a cancel button
		canc_btn = ttk.Button(msg_widget['frame'], text='Cancel', width=6, command=lambda: on_cancel())
		canc_btn.pack(side='right', padx=3)

		# Create a send button to confirm edits
		send_btn = ttk.Button(msg_widget['frame'], text='Send', width=4, command=lambda: on_confirm())
		send_btn.pack(side='right', padx=3)

		# Function to handle cancelling of edits
		def on_cancel():
			# Remove edit entry elements and repack the original message and edit button
			canc_btn.destroy()
			send_btn.destroy()
			edit_ent.destroy()

			msg_widget['edit'].pack(side='bottom', anchor='se', padx=(0, msg_widget['padxr']))
			msg_widget['label'].pack(side='right', anchor='e', padx=(msg_widget['padxl'], msg_widget['padxr']), expand=True)

		# Function to handle confirmation of edits
		def on_confirm():
			new_text = edit_ent.get()
			if new_text:
				# Backup the current state of chatlog
				self.backup_chatlog()

				# Delete all messages after this point
				self.delete_messages(msg_id)

				# Send the updated message
				self.msg_ent.insert(0, new_text)
				self.send_message()

		# Allow user to hit enter instead of the send button
		edit_ent.bind('<Return>', lambda event: on_confirm())

		edit_ent.focus_set()
		edit_ent.select_range(0, 'end')

	def get_llm_response(self):
		"""
		Retreives the LLM response given the current chat log and the true model
		"""
		# Create a prompt of the current chatlog
		prompt = self.concat_conversation()

		# Get a response from the true model
		model_function_map = {
			'gpt-4o-mini': self.config['openai'].gpt_chat,
			'meta-llama/Meta-Llama-3-70B-Instruct': self.config['anyscale'].anyscale_chat,
			'claude-3-haiku-20240307': self.config['anthropic'].claude_chat
		}
		chat_function = model_function_map.get(self.config['true_model'])
		rsp = chat_function(prompt, self.config['true_model']) if chat_function else None

		if rsp: # Check if the LLM actually responded
			msg_id = len(self.chatlog) + 1
			rsp_info = {
				'msg_id': msg_id,
				'sender': 'Bot',
				'content': rsp
			}

			# Update the chat log, remove thinking dots, and draw the message to the screen
			self.dots_label.pack_forget()
			self.chatlog.append(rsp_info)
			self.update_window(rsp_info)
		else:
			print("There was an error getting a response.")

	def update_window(self, msg_info):
		"""
		Updates the chat log with the current message and draws it to the screen
		:param msg_info: Dictionary containing message id, sender, and content
		"""
		msg = msg_info['content']
		send = msg_info['sender']
		# Determine color and alignment based on the sender
		if send == "User":
			if self.root.tk.call("ttk::style", "theme", "use") == "azure-dark":
				bg_color = colors.get("user_msg_bg_dark")
				text_color = colors.get("user_msg_text_dark")
			else:
				bg_color = colors.get("user_msg_bg_light")
				text_color = colors.get("user_msg_text_light")
			icon = self.user_icon
			anchor = 'e'
			side = 'right'
			padx_right = 10
			padx_left = max(100, 250 - len(msg)*7)  # Dynamic left padding based on message length
		else:
			if self.root.tk.call("ttk::style", "theme", "use") == "azure-dark":
				bg_color = colors.get("bot_msg_bg_dark")
				text_color = colors.get("user_msg_text_dark")
			else:	
				bg_color = colors.get("bot_msg_bg_light")
				text_color = colors.get("user_msg_text_light")
			icon = self.bot_icon
			anchor = 'w'
			side = 'left'
			padx_left = 10
			padx_right = max(100, 250 - len(msg)*7)  # Dynamic right padding based on message length

		# Create a frame to contain the message label and pack it to the correct side
		frame = ttk.Frame(self.scrollable_window)
		frame.pack(fill='x', expand=True, pady=0)

		# Add icons for the message to indicate who is speaking
		icon_label = tk.Label(frame, image=icon)
		icon_label.pack(side=side, anchor='n', padx=(padx_left if send == "Bot" else 0, padx_right if send == "User" else 0))

		# If the sender is a user, add a button to edit the message
		if send == "User":
			edit_btn = tk.Button(frame, image=self.edit_icon, bg=colors.get("edit_button_bg"), command=lambda msg_id=msg_info['msg_id']: self.edit_message(msg_id))
			edit_btn.pack(side='bottom', anchor='se', padx=(0, padx_right))

		# Create a label inside the frame that contains the message contents
		msg_label = tk.Label(frame, text=msg, bg=bg_color, fg=text_color, font=('Arial', 14), justify='left', wraplength=500)
		msg_label.pack(side=side, anchor=anchor, padx=(padx_left, padx_right))

		# Update the dictionary of widgets with the important information based on sender
		if send == "User":
			self.msg_widgets[msg_info['msg_id']] = {'frame': frame, 'label': msg_label, 'info': msg_info, 'edit': edit_btn, 'padxr': padx_right, 'padxl': padx_left}
		else:
			self.msg_widgets[msg_info['msg_id']] = {'frame': frame, 'label': msg_label, 'info': msg_info}

		# Scroll to the bottom of the chat window as new messages are added
		self.canvas.update_idletasks()
		self.canvas.yview_moveto(1)

	def delete_messages(self, msg_id):
		"""
		Removes all message from chat log and screen from a specified message
		:param msg_id: Id number of message to be deleted along with subsequent messages
		"""
		# Remove messages from UI and chatlog
		ids = [id for id in self.msg_widgets if id >= msg_id]
		for id in ids:
			widget = self.msg_widgets[id]
			widget['frame'].destroy()  # Remove the frame from UI
			del self.msg_widgets[id]  # Remove from widget storage
			self.chatlog = [msg for msg in self.chatlog if msg['msg_id'] < msg_id]  # Trim the chat log

	def backup_chatlog(self):
		"""
		Backs up the current chat log so that edits can be saved
		"""
		chat_id = len(self.conversations) + 1
		self.conversations[chat_id] = {'chat_id': chat_id, 'chatlog': self.chatlog}

	def concat_conversation(self):
		"""
		Concatenates all chat log entry contents in a single model prompt
		"""
		conv = ""
		for msg in self.chatlog:
			#prefix = "User: " if msg['sender'] == 'User' else "Model:"
			conv += f"{msg['content']}\n"
		return conv.strip()

	def update_scrollregion(self, event=None):
		"""
		Updates the scroll region of the canvas based on the bounding box of all items.
		"""
		self.canvas.configure(scrollregion=self.canvas.bbox("all"))


	def resize_canvas(self, event):
		"""
		Adjusts the width of the scrollable window to match the canvas's width.
		"""
		self.canvas.itemconfig(self.canvas_window, width=event.width)
		 

	def on_mousewheel(self, event):
		"""
		Scrolls the canvas content when the mouse wheel is used
		"""
		self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")


	def change_theme(self):
		"""
		Changes the imported theme and custom elements between dark and light mode
		"""
		if self.root.tk.call("ttk::style", "theme", "use") == "azure-dark":
			self.root.tk.call("set_theme", "light")
			ids = [id for id in self.msg_widgets]
			for id in ids:
				widget = self.msg_widgets[id]
				if widget['info']['sender'] == "User":
					widget['label'].config(bg=colors.get("user_msg_bg_light"), fg=colors.get("user_msg_text_light"))
				else:
					widget['label'].config(bg=colors.get("bot_msg_bg_light"), fg=colors.get("user_msg_text_light"))
		else:
			self.root.tk.call("set_theme", "dark")
			ids = [id for id in self.msg_widgets]
			for id in ids:
				widget = self.msg_widgets[id]
				if widget['info']['sender'] == "User":
					widget['label'].config(bg=colors.get("user_msg_bg_dark"), fg=colors.get("user_msg_text_dark"))
				else:
					widget['label'].config(bg=colors.get("bot_msg_bg_dark"), fg=colors.get("user_msg_text_dark"))


	def on_close(self):
		"""
		Handles saving the chat log history to a json file on close of the program
		"""
		self.backup_chatlog()
		save_json_data(self.conversations, "Conversations.json")
		self.root.destroy()


def main():
	# Get the command line parameters from the command line arguments
	args = parse_arguments()
	config = {
		'given_model': args.given_model,
		'true_model': model_name_mapping.get(args.true_model, "Invalid model."),
		'openai': openaiHandler(api_key=args.openai_key),
		'anyscale': anyscaleHandler(api_key=args.anyscale_key),
		'anthropic': anthropicHandler(api_key=args.anthropic_key)
	}

	# Initialize Tkinter window
	root = tk.Tk()
	root.geometry('1200x900')
	#root.geometry('800x600')
	root.tk.call("source", "Azure-ttk-theme-main/azure.tcl")
	root.tk.call("set_theme", "dark")
	app = ChatApp(root, config)
	root.mainloop()


if __name__ == "__main__":
	main()