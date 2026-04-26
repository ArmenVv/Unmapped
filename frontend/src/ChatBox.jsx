import { useState } from "react"

export default function ChatBox() {
  const [text, setText] = useState("")

  function sendMessage() {
    if (!text.trim()) return

    console.log("User prompt:", text)
    setText("")
  }

  return (
    <div className="prompt-box">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        placeholder="Ask anything..."
      />

      <button onClick={sendMessage}>
        ↑
      </button>
    </div>
  )
}