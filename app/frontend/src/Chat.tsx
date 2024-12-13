import { useEffect, useCallback, useState } from "react";
import { MessageCircle, Send, SidebarCloseIcon } from "lucide-react";
import { tailspin } from "ldrs";

type Message = {
  type: string;
  content: string;
  source: string;
};

const ChatInterface = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(async () => {
    if (!input.trim()) return;

    const userMessage = input.trim();
    setInput("");

    console.log("Before user message update:", messages);

    // Update with user message
    setMessages((prevMessages) => {
      console.log("Updating with user message, prev:", prevMessages);
      return [...prevMessages, { type: "user", content: userMessage }];
    });

    setIsLoading(true);

    try {
      console.log("Sending API request...");
      const response = await fetch("http://127.0.0.1:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userMessage }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (!data || typeof data.answer === "undefined") {
        throw new Error("Invalid response format from API");
      }

      // Update with bot response
      setMessages((prevMessages) => {
        console.log("Updating with bot message, prev:", prevMessages);
        return [
          ...prevMessages,
          { type: "bot", content: data.answer, source: data.sources },
        ];
      });
    } catch (error) {
      console.error("Chat error:", error);
      setMessages((prevMessages) => [
        ...prevMessages,
        {
          type: "error",
          content: "Sorry, I encountered an error. Please try again.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [input, messages]);

  // Effect for monitoring messages changes
  useEffect(() => {
    console.log("Messages updated:", messages);
  }, [messages]);

  tailspin.register();
  return (
    <div className="fixed bottom-4 right-4">
      {!isOpen ? (
        <button
          onClick={() => setIsOpen(true)}
          className="bg-blue-600 p-4 rounded-full shadow-lg hover:bg-blue-700"
        >
          <MessageCircle className="w-6 h-6 text-white" />
        </button>
      ) : (
        <div className="bg-white rounded-lg shadow-xl w-96 h-[500px] flex flex-col">
          <div className="p-4 bg-blue-600 flex justify-between items-center text-white rounded-t-lg">
            <h2 className="text-lg font-semibold">Nestlé Assistant</h2>
            <button
              onClick={() => setIsOpen(false)}
              className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <SidebarCloseIcon className="w-5 h-5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.type === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`p-3 rounded-lg max-w-[80%] text-black text-start ${
                    msg.type === "user" ? "bg-blue-100" : "bg-gray-100"
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {isLoading && (
              <l-tailspin
                size={40}
                stroke={5}
                speed={0.9}
                color={"black"}
              ></l-tailspin>
            )}
          </div>

          <div className="p-4 border-t">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && sendMessage()}
                className="flex-1 p-2 border rounded-lg bg-gray-100 text-black"
                placeholder="Type your message..."
              />
              <button
                onClick={sendMessage}
                className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatInterface;
