import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
import matplotlib.pyplot as plt
import numpy as np

# Set device
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'Using device: {device}')

np.random.seed(42)                  
torch.manual_seed(42) 

# Define the Basic Block for ResNet
class BasicBlock(nn.Module):
    expansion = 1
    
    def __init__(self, in_planes, planes, stride=1):
        super(BasicBlock, self).__init__()
        # First convolutional layer
        self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=3, stride=stride, 
                              padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        
        # Second convolutional layer
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=1, 
                              padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        
        # Shortcut connection
        self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != self.expansion * planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_planes, self.expansion * planes, kernel_size=1, 
                         stride=stride, bias=False),
                nn.BatchNorm2d(self.expansion * planes)
            )
    
    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)  # Residual connection
        out = F.relu(out)
        return out

# Define the ResNet model
class ResNet(nn.Module):
    def __init__(self, block, num_blocks, num_classes=10):
        super(ResNet, self).__init__()
        self.in_planes = 64
        
        # Initial preprocessing convolutional layer (not counted in 17 layers)
        self.conv1 = nn.Conv2d(1, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        
        # ResNet layers (16 conv layers + 1 FC = 17 layers total)
        self.layer1 = self._make_layer(block, 64, num_blocks[0], stride=1)   # 4 conv layers
        self.layer2 = self._make_layer(block, 128, num_blocks[1], stride=2)  # 4 conv layers
        self.layer3 = self._make_layer(block, 256, num_blocks[2], stride=2)  # 4 conv layers
        self.layer4 = self._make_layer(block, 512, num_blocks[3], stride=2)  # 4 conv layers
        
        # Global average pooling and fully connected layer
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(512 * block.expansion, num_classes)  # 1 FC layer
        
        # Dropout for regularization
        self.dropout = nn.Dropout(0.2)
        
    def _make_layer(self, block, planes, num_blocks, stride):
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_planes, planes, stride))
            self.in_planes = planes * block.expansion
        return nn.Sequential(*layers)
    
    def forward(self, x):
        # Initial preprocessing layer
        out = F.relu(self.bn1(self.conv1(x)))
        
        # ResNet layers with residual connections
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        
        # Global average pooling
        out = self.avgpool(out)
        out = torch.flatten(out, 1)
        
        # Dropout and fully connected layer
        out = self.dropout(out)
        out = self.fc(out)
        
        return out

# Function to create ResNet-18
def ResNet18(num_classes=10):
    return ResNet(BasicBlock, [2, 2, 2, 2], num_classes)

# Data preprocessing and loading
def get_data_loaders(batch_size=64):
    # Define transforms for the training and test sets
    # Data augmentation for training
    train_transform = transforms.Compose([
        transforms.RandomRotation(10),
        transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))  # MNIST mean and std
    ])
    
    test_transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    
    # Download and load the training data
    train_dataset = datasets.MNIST('data', train=True, download=True, transform=train_transform)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    
    # Download and load the test data
    test_dataset = datasets.MNIST('data', train=False, download=True, transform=test_transform)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    return train_loader, test_loader

# Training function
def train_model(model, train_loader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    for batch_idx, (data, target) in enumerate(train_loader):
        data, target = data.to(device), target.to(device)
        
        # Zero the parameter gradients
        optimizer.zero_grad()
        
        # Forward pass
        outputs = model(data)
        loss = criterion(outputs, target)
        
        # Backward pass and optimize
        loss.backward()
        optimizer.step()
        
        # Statistics
        running_loss += loss.item()
        _, predicted = torch.max(outputs.data, 1)
        total += target.size(0)
        correct += (predicted == target).sum().item()
        
        if batch_idx % 200 == 0:
            print(f'Batch {batch_idx}, Loss: {loss.item():.4f}')
    
    epoch_loss = running_loss / len(train_loader)
    epoch_acc = 100 * correct / total
    
    return epoch_loss, epoch_acc

# Testing function
def test_model(model, test_loader, criterion, device):
    model.eval()
    test_loss = 0.0
    correct = 0
    total = 0
    
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            outputs = model(data)
            loss = criterion(outputs, target)
            
            test_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += target.size(0)
            correct += (predicted == target).sum().item()
    
    test_loss /= len(test_loader)
    test_acc = 100 * correct / total
    
    return test_loss, test_acc

# Function to visualize model architecture
def print_model_summary(model, input_size=(1, 1, 28, 28)):
    print("ResNet-18 Architecture Summary:")
    print("=" * 60)
    
    # Count layers
    conv_layers = 0
    fc_layers = 0
    
    for name, module in model.named_modules():
        if isinstance(module, nn.Conv2d):
            conv_layers += 1
        elif isinstance(module, nn.Linear):
            fc_layers += 1
    
    print(f"Total Convolutional Layers: {conv_layers}")
    print(f"Total Fully Connected Layers: {fc_layers}")
    print(f"Total Trainable Layers: {conv_layers + fc_layers}")
    
    # Create a dummy input to get output shapes
    dummy_input = torch.randn(input_size)
    
    print(f"\nInput shape: {dummy_input.shape}")
    
    # Register hooks to capture intermediate shapes
    shapes = {}
    def hook_fn(name):
        def hook(module, input, output):
            shapes[name] = output.shape
        return hook
    
    # Register hooks for main layers
    model.conv1.register_forward_hook(hook_fn('conv1'))
    model.layer1.register_forward_hook(hook_fn('layer1'))
    model.layer2.register_forward_hook(hook_fn('layer2'))
    model.layer3.register_forward_hook(hook_fn('layer3'))
    model.layer4.register_forward_hook(hook_fn('layer4'))
    model.avgpool.register_forward_hook(hook_fn('avgpool'))
    model.fc.register_forward_hook(hook_fn('fc'))
    
    # Forward pass
    with torch.no_grad():
        _ = model(dummy_input)
    
    # Print shapes
    for layer_name, shape in shapes.items():
        print(f"After {layer_name}: {shape}")
    
    print("=" * 60)

# Main training loop
def main():
    # Hyperparameters
    batch_size = 64
    learning_rate = 0.001
    num_epochs = 15  # More epochs for deeper network
    
    # Get data loaders
    train_loader, test_loader = get_data_loaders(batch_size)
    
    # Initialize the model
    model = ResNet18().to(device)
    print(f"Model architecture:\n{model}")
    
    # Print model summary
    print_model_summary(model)
    
    # Print model parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\nTotal parameters: {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,}")
    
    # Define loss function and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    
    # Learning rate scheduler
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=7, gamma=0.1)
    
    # Training history
    train_losses = []
    train_accuracies = []
    test_losses = []
    test_accuracies = []
    
    # Training loop
    print("\nStarting training...")
    for epoch in range(num_epochs):
        print(f'\nEpoch [{epoch+1}/{num_epochs}]')
        print(f'Learning Rate: {optimizer.param_groups[0]["lr"]:.6f}')
        
        # Train
        train_loss, train_acc = train_model(model, train_loader, criterion, optimizer, device)
        
        # Test
        test_loss, test_acc = test_model(model, test_loader, criterion, device)
        
        # Update learning rate
        scheduler.step()
        
        # Store history
        train_losses.append(train_loss)
        train_accuracies.append(train_acc)
        test_losses.append(test_loss)
        test_accuracies.append(test_acc)
        
        print(f'Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%')
        print(f'Test Loss: {test_loss:.4f}, Test Acc: {test_acc:.2f}%')
    
    print(f'\nTraining completed!')
    print(f'Final Test Accuracy: {test_accuracies[-1]:.2f}%')
    
    # Plot training history
    plot_training_history(train_losses, train_accuracies, test_losses, test_accuracies)
    
    # Visualize feature maps
    visualize_feature_maps(model, test_loader, device)
    
    # Save the model
    torch.save(model.state_dict(), 'mnist_resnet18_model.pth')
    print("Model saved as 'mnist_resnet18_model.pth'")
    
    return model

# Function to plot training history
def plot_training_history(train_losses, train_accuracies, test_losses, test_accuracies):
    epochs = range(1, len(train_losses) + 1)
    
    plt.figure(figsize=(12, 4))
    
    # Plot loss
    plt.subplot(1, 2, 1)
    plt.plot(epochs, train_losses, 'b-', label='Training Loss')
    plt.plot(epochs, test_losses, 'r-', label='Test Loss')
    plt.title('ResNet-18 Model Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()
    plt.grid(True)
    
    # Plot accuracy
    plt.subplot(1, 2, 2)
    plt.plot(epochs, train_accuracies, 'b-', label='Training Accuracy')
    plt.plot(epochs, test_accuracies, 'r-', label='Test Accuracy')
    plt.title('ResNet-18 Model Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy (%)')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    plt.show()

# Function to visualize feature maps from different layers
def visualize_feature_maps(model, test_loader, device):
    model.eval()
    
    # Get a sample image
    data_iter = iter(test_loader)
    images, _ = next(data_iter)
    sample_image = images[0:1].to(device)  # Take first image
    
    # Hook to capture feature maps
    feature_maps = {}
    
    def hook_fn(name):
        def hook(module, input, output):
            feature_maps[name] = output.detach().cpu()
        return hook
    
    # Register hooks for different layers
    model.conv1.register_forward_hook(hook_fn('conv1'))
    model.layer1[0].conv1.register_forward_hook(hook_fn('layer1_block1_conv1'))
    model.layer2[0].conv1.register_forward_hook(hook_fn('layer2_block1_conv1'))
    model.layer3[0].conv1.register_forward_hook(hook_fn('layer3_block1_conv1'))
    
    # Forward pass
    with torch.no_grad():
        _ = model(sample_image)
    
    # Visualize feature maps
    plt.figure(figsize=(16, 4))
    
    # Original image
    plt.subplot(1, 5, 1)
    plt.imshow(sample_image.cpu().squeeze(), cmap='gray')
    plt.title('Original Image')
    plt.axis('off')
    
    # Feature maps from different layers
    layer_names = ['conv1', 'layer1_block1_conv1', 'layer2_block1_conv1', 'layer3_block1_conv1']
    titles = ['Conv1 (64 ch)', 'Layer1 (64 ch)', 'Layer2 (128 ch)', 'Layer3 (256 ch)']
    
    for i, (layer_name, title) in enumerate(zip(layer_names, titles)):
        if layer_name in feature_maps:
            features = feature_maps[layer_name][0]  # Remove batch dimension
            # Show the first channel
            plt.subplot(1, 5, i + 2)
            plt.imshow(features[0], cmap='gray')
            plt.title(title)
            plt.axis('off')
    
    plt.tight_layout()
    plt.show()
    
    # Show multiple channels from conv1
    if 'conv1' in feature_maps:
        conv1_features = feature_maps['conv1'][0]
        plt.figure(figsize=(12, 8))
        for i in range(min(8, conv1_features.size(0))):
            plt.subplot(2, 4, i + 1)
            plt.imshow(conv1_features[i], cmap='gray')
            plt.title(f'Conv1 Channel {i+1}')
            plt.axis('off')
        plt.suptitle('Conv1 Feature Maps (First 8 channels)')
        plt.tight_layout()
        plt.show()

# Function to test with sample images
def test_sample_predictions(model, test_loader, device, num_samples=10):
    model.eval()
    
    # Get a batch of test data
    data_iter = iter(test_loader)
    images, labels = next(data_iter)
    
    # Select first num_samples
    sample_images = images[:num_samples]
    sample_labels = labels[:num_samples]
    
    # Make predictions
    with torch.no_grad():
        sample_images_gpu = sample_images.to(device)
        outputs = model(sample_images_gpu)
        probabilities = F.softmax(outputs, dim=1)
        _, predicted = torch.max(outputs, 1)
        confidence = torch.max(probabilities, 1)[0]
    
    # Plot results
    plt.figure(figsize=(15, 3))
    for i in range(num_samples):
        plt.subplot(1, num_samples, i + 1)
        plt.imshow(sample_images[i].squeeze(), cmap='gray')
        plt.title(f'True: {sample_labels[i].item()}\nPred: {predicted[i].item()}\nConf: {confidence[i].item():.2f}')
        plt.axis('off')
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # Train the model
    trained_model = main()
    
    # Test with sample predictions
    print("\nTesting with sample images...")
    _, test_loader = get_data_loaders(batch_size=64)
    test_sample_predictions(trained_model, test_loader, device)