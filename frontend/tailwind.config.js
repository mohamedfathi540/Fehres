/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: {
                    50: "var(--color-primary-50)",
                    100: "var(--color-primary-100)",
                    200: "var(--color-primary-200)",
                    300: "var(--color-primary-300)",
                    400: "var(--color-primary-400)",
                    500: "var(--color-primary-500)",
                    600: "var(--color-primary-600)",
                    700: "var(--color-primary-700)",
                    800: "var(--color-primary-800)",
                    900: "var(--color-primary-900)",
                },
                success: "var(--color-success)",
                warning: "var(--color-warning)",
                error: "var(--color-error)",
                bg: {
                    primary: "var(--color-bg-primary)",
                    secondary: "var(--color-bg-secondary)",
                    tertiary: "var(--color-bg-tertiary)",
                    card: "var(--color-bg-card)",
                    hover: "var(--color-bg-hover)",
                    pressed: "var(--color-bg-pressed)",
                },
                text: {
                    primary: "var(--color-text-primary)",
                    secondary: "var(--color-text-secondary)",
                    muted: "var(--color-text-muted)",
                },
                border: {
                    DEFAULT: "var(--color-border)",
                    hover: "var(--color-border-hover)",
                },
            },
            borderRadius: {
                sm: "var(--radius-sm)",
                md: "var(--radius-md)",
                lg: "var(--radius-lg)",
                xl: "var(--radius-xl)",
            },
        },
    },
    plugins: [],
}
