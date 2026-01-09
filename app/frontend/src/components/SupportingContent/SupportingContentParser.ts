import DOMPurify from "dompurify";

type ParsedSupportingContentItem = {
    title: string;
    content: string;
    availability?: string;
};

export function parseSupportingContentItem(item: string): ParsedSupportingContentItem {
    // Assumes the item starts with the file name followed by : and the content.
    // Example: "sdp_corporate.pdf: this is the content that follows".
    const parts = item.split(": ");
    const title = parts[0];
    const rawContent = parts.slice(1).join(": ");
    const availabilityMatch = rawContent.match(/Availability:\\s*([0-9.]+)/i);
    let content = rawContent;
    if (availabilityMatch) {
        content = rawContent.replace(availabilityMatch[0], "").replace(/;\\s*\\.?$/, "");
    }
    const sanitizedContent = DOMPurify.sanitize(content);
    let availability: string | undefined;
    if (availabilityMatch) {
        const parsed = Number(availabilityMatch[1]);
        if (Number.isFinite(parsed)) {
            availability = `${Math.round(parsed * 100)}%`;
        } else {
            availability = availabilityMatch[1];
        }
    }

    return {
        title,
        content: sanitizedContent,
        availability
    };
}
