package functions;

import com.google.cloud.functions.BackgroundFunction;
import com.google.cloud.functions.Context;
import com.sendgrid.Method;
import com.sendgrid.Request;
import com.sendgrid.Response;
import com.sendgrid.SendGrid;
import com.sendgrid.helpers.mail.Mail;
import com.sendgrid.helpers.mail.objects.Content;
import com.sendgrid.helpers.mail.objects.Email;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Map;
import java.util.logging.Logger;

public class EmailSender implements BackgroundFunction<EmailSender.PubSubMessage> {
    private static final Logger logger = Logger.getLogger(EmailSender.class.getName());
    private static final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public void accept(PubSubMessage message, Context context) {
        if (message.data == null) {
            logger.warning("No message data found");
            return;
        }

        try {
            String data = new String(Base64.getDecoder().decode(message.data), StandardCharsets.UTF_8);
            Map<String, String> emailData = objectMapper.readValue(data, Map.class);
            
            String to = emailData.get("to");
            String subject = emailData.get("subject");
            String body = emailData.get("body");

            sendEmail(to, subject, body);
            
        } catch (Exception e) {
            logger.severe("Error processing message: " + e.getMessage());
            throw new RuntimeException(e);
        }
    }

    private void sendEmail(String to, String subject, String body) throws Exception {
        Email from = new Email("heath352.451@gmail.com");
        Email toEmail = new Email(to);
        Content content = new Content("text/html", body);
        Mail mail = new Mail(from, subject, toEmail, content);

        String apiKey = System.getenv("SENDGRID_API_KEY");
        if (apiKey == null || apiKey.isEmpty()) {
            logger.severe("SENDGRID_API_KEY environment variable not set");
            return;
        }

        SendGrid sg = new SendGrid(apiKey);
        Request request = new Request();
        request.setMethod(Method.POST);
        request.setEndpoint("mail/send");
        request.setBody(mail.build());

        Response response = sg.api(request);
        logger.info("Email sent. Status Code: " + response.getStatusCode());
        
        if (response.getStatusCode() >= 400) {
            logger.severe("Failed to send email: " + response.getBody());
        }
    }

    public static class PubSubMessage {
        public String data;
        public Map<String, String> attributes;
        public String messageId;
        public String publishTime;
    }
}
