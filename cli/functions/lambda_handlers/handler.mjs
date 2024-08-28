import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const loadModule = async (modulePath) => {
    try {
        return await import(modulePath);
    } catch (e) {
        console.error("Error loading module:", e);
        return null;
    }
};

export async function main(event, context) {
    const modulePath = path.join(__dirname, './main.js');

    const functionModule = await loadModule(modulePath);
    if (!functionModule || !functionModule.main) {
        return {
            statusCode: 500,
            body: JSON.stringify({
                error: "The main function could not be loaded.",
                detail: "Module or main function is missing.",
            }),
        };
    }

    try {
        const result = await functionModule.main(event);
        return result;
    } catch (e) {
        return {
            statusCode: 500,
            body: JSON.stringify({
                error: e.message,
                trace: e.stack,
            }),
        };
    }
}
