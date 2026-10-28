import styles from "./Button.module.css";

const classes = (...values) =>
  values.filter(Boolean).join(" ");

export function Button({
  children,
  variant = "ghost",
  size = "md",
  type = "button",
  loading = false,
  disabled,
  className,
  ...props
}) {
  const isDisabled = loading || disabled;

  return (
    <button
      type={type}
      className={classes(
        styles.button,
        styles[variant],
        styles[size],
        loading && styles.loading,
        className
      )}
      disabled={isDisabled}
      {...props}
    >
      {children}
    </button>
  );
}

export function IconButton({
  children,
  variant = "ghost",
  size = "md",
  className,
  ...props
}) {
  return (
    <button
      type="button"
      className={classes(styles.iconButton, styles[variant], styles[size], className)}
      {...props}
    >
      {children}
    </button>
  );
}
