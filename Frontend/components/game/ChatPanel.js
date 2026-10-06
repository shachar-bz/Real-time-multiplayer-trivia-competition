"use client";

import { cx } from "@/lib/classNames";
import styles from "./GameScreen.module.css";

/** In-game chat: a floating button with an unread badge, or the open message panel. */
export default function ChatPanel({
  chatInput,
  chatListRef,
  chatMessages,
  chatOpen,
  chatUnreadCount,
  onChatInputChange,
  onCloseChat,
  onOpenChat,
  onSendChatMessage,
}) {
  if (!chatOpen) {
    return (
      <aside className={styles.chatDock} aria-label="Game chat">
        <button className={styles.chatToggle} onClick={onOpenChat} type="button" aria-label="Open chat">
          <span className={styles.chatGlyph} aria-hidden="true" />
          {chatUnreadCount > 0 && <span className={styles.chatBadge}>{chatUnreadCount}</span>}
        </button>
      </aside>
    );
  }

  return (
    <aside className={cx(styles.chatDock, styles.chatOpen)} aria-label="Game chat">
      <div className={styles.chatHeader}>
        <strong>Chat</strong>
        <button className={styles.chatClose} onClick={onCloseChat} type="button" aria-label="Close chat">
          x
        </button>
      </div>
      <div className={styles.chatMessages} ref={chatListRef}>
        {chatMessages.map((message) => (
          <article
            className={cx(styles.chatMessage, message.is_own ? styles.chatMessageOwn : "")}
            key={message.id}
          >
            <span className={styles.chatUsername}>{message.username}</span>
            <p>{message.content}</p>
            <time>{message.timestamp}</time>
          </article>
        ))}
      </div>
      <form className={styles.chatForm} onSubmit={onSendChatMessage}>
        <input
          aria-label="Chat message"
          maxLength={240}
          onChange={(event) => onChatInputChange(event.target.value)}
          placeholder="Type a message"
          value={chatInput}
        />
        <button type="submit">Send</button>
      </form>
    </aside>
  );
}
