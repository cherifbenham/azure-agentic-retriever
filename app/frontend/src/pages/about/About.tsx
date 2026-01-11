import { Helmet } from "react-helmet-async";
import { useTranslation } from "react-i18next";
import styles from "./About.module.css";

export function Component(): JSX.Element {
    const { t } = useTranslation();

    return (
        <div className={styles.page}>
            <Helmet>
                <title>{t("aboutTitle")}</title>
            </Helmet>
            <section className={styles.hero}>
                <p className={styles.eyebrow}>{t("aboutEyebrow")}</p>
                <h1 className={styles.title}>{t("aboutTitle")}</h1>
                <p className={styles.subtitle}>{t("aboutSubtitle")}</p>
            </section>
            <section className={styles.grid}>
                <div className={styles.card}>
                    <h3>{t("aboutPoint1Title")}</h3>
                    <p>{t("aboutPoint1Body")}</p>
                </div>
                <div className={styles.card}>
                    <h3>{t("aboutPoint2Title")}</h3>
                    <p>{t("aboutPoint2Body")}</p>
                </div>
                <div className={styles.card}>
                    <h3>{t("aboutPoint3Title")}</h3>
                    <p>{t("aboutPoint3Body")}</p>
                </div>
            </section>
            <section className={styles.cta}>
                <p>{t("aboutCtaBody")}</p>
                <a className={styles.ctaLink} href="#/">
                    {t("aboutCtaLink")}
                </a>
            </section>
        </div>
    );
}

Component.displayName = "About";
