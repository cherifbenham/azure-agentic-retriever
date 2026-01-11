import { Helmet } from "react-helmet-async";
import { useTranslation } from "react-i18next";
import styles from "./Contact.module.css";

export function Component(): JSX.Element {
    const { t } = useTranslation();

    return (
        <div className={styles.page}>
            <Helmet>
                <title>{t("contactTitle")}</title>
            </Helmet>
            <section className={styles.hero}>
                <p className={styles.eyebrow}>{t("contactEyebrow")}</p>
                <h1 className={styles.title}>{t("contactTitle")}</h1>
                <p className={styles.subtitle}>{t("contactSubtitle")}</p>
            </section>
            <section className={styles.actions}>
                <div className={styles.card}>
                    <h3>{t("contactPrimaryTitle")}</h3>
                    <p>{t("contactPrimaryBody")}</p>
                    <a className={styles.primaryButton} href="mailto:expert-matcher@alten.com">
                        {t("contactPrimaryCta")}
                    </a>
                </div>
                <div className={styles.card}>
                    <h3>{t("contactSecondaryTitle")}</h3>
                    <p>{t("contactSecondaryBody")}</p>
                    <a className={styles.secondaryButton} href="mailto:expert-matcher@alten.com?subject=Expert%20booking%20request">
                        {t("contactSecondaryCta")}
                    </a>
                </div>
            </section>
            <section className={styles.detail}>
                <p>{t("contactNote")}</p>
            </section>
        </div>
    );
}

Component.displayName = "Contact";
