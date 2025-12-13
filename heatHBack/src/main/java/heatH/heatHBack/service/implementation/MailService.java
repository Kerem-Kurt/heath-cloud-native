package heatH.heatHBack.service.implementation;

import com.google.cloud.pubsub.v1.Publisher;
import com.google.protobuf.ByteString;
import com.google.pubsub.v1.PubsubMessage;
import com.google.pubsub.v1.TopicName;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Service
@RequiredArgsConstructor
public class MailService {

    @Value("${gcp.project-id}")
    private String projectId;

    @Value("${gcp.pubsub.topic-id:send-email}")
    private String topicId;

    @Value("${app.base-url}")
    private String baseUrl;

    private final ObjectMapper objectMapper;

    public void sendEmail(String to, String subject, String body) {
        try {
            TopicName topicName = TopicName.of(projectId, topicId);
            Publisher publisher = Publisher.newBuilder(topicName).build();

            Map<String, String> emailData = new HashMap<>();
            emailData.put("to", to);
            emailData.put("subject", subject);
            emailData.put("body", body);

            String jsonMessage = objectMapper.writeValueAsString(emailData);
            ByteString data = ByteString.copyFromUtf8(jsonMessage);

            PubsubMessage pubsubMessage = PubsubMessage.newBuilder().setData(data).build();

            publisher.publish(pubsubMessage).get();
            System.out.println("Published message to " + topicId + ": " + jsonMessage);

            publisher.shutdown();
            publisher.awaitTermination(1, TimeUnit.MINUTES);

        } catch (Exception e) {
            throw new RuntimeException("Failed to publish email message to Pub/Sub", e);
        }
    }
}
