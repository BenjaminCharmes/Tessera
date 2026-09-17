import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // Deux crans sous `text-xs`, nommés plutôt qu'écrits en dur dans les
      // composants. Une échelle nommée est un choix qu'on relit ; un
      // `text-[9px]` posé au fil d'un ticket est une échappatoire, et c'est
      // ainsi qu'on s'était retrouvé avec trois tailles arbitraires
      // (ticket-067).
      fontSize: {
        micro: ["0.625rem", { lineHeight: "0.875rem" }],
        mini: ["0.6875rem", { lineHeight: "1rem" }],
      },
    },
  },
  plugins: [],
};

export default config;
