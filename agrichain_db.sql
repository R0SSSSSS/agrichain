-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1:3306
-- Generation Time: May 02, 2026 at 11:30 AM
-- Server version: 9.1.0
-- PHP Version: 8.3.14

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `agrichain_db`
--

-- --------------------------------------------------------

--
-- Table structure for table `complaint`
--

DROP TABLE IF EXISTS `complaint`;
CREATE TABLE IF NOT EXISTS `complaint` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `order_id` int DEFAULT NULL,
  `subject` varchar(150) NOT NULL,
  `message` text NOT NULL,
  `status` varchar(50) DEFAULT NULL,
  `resolution` text,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `resolved_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `order_id` (`order_id`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `complaint`
--

INSERT INTO `complaint` (`id`, `user_id`, `order_id`, `subject`, `message`, `status`, `resolution`, `created_at`, `updated_at`, `resolved_at`) VALUES
(1, 4, 6, 'order is taking so long', 'its been 2 weeks', 'In Review', 'where getting on it', '2026-05-02 04:54:34', '2026-05-02 07:18:50', NULL);

-- --------------------------------------------------------

--
-- Table structure for table `delivery_proof`
--

DROP TABLE IF EXISTS `delivery_proof`;
CREATE TABLE IF NOT EXISTS `delivery_proof` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL,
  `image` varchar(200) NOT NULL,
  `note` text,
  `uploaded_by` int NOT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `order_id` (`order_id`),
  KEY `uploaded_by` (`uploaded_by`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `notification`
--

DROP TABLE IF EXISTS `notification`;
CREATE TABLE IF NOT EXISTS `notification` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `message` varchar(255) DEFAULT NULL,
  `is_read` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`)
) ENGINE=MyISAM AUTO_INCREMENT=48 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `notification`
--

INSERT INTO `notification` (`id`, `user_id`, `message`, `is_read`, `created_at`) VALUES
(1, 5, 'New order for kangkong', 0, '2026-04-25 02:21:31'),
(2, 5, 'New order for kangkong', 0, '2026-04-25 02:29:54'),
(3, 5, 'New order for kangkong', 0, '2026-04-25 02:31:12'),
(4, 5, 'New order for Apples', 0, '2026-04-25 04:10:26'),
(5, 5, 'New COD order for Apples. Please confirm the buyer address.', 0, '2026-04-25 05:11:28'),
(6, 4, 'Your order for Apples was placed. Seller will confirm your address.', 0, '2026-04-25 05:11:28'),
(7, 5, 'Buyer confirmed address for order #5', 0, '2026-04-25 05:11:51'),
(8, 4, 'New message about order #5', 0, '2026-04-25 05:13:29'),
(9, 4, 'Your order for Apples was approved and is being prepared.', 0, '2026-04-25 05:13:38'),
(10, 5, 'Your product kangkong was approved and is now visible in the marketplace.', 0, '2026-04-30 01:46:16'),
(11, 5, 'Your product kangkong was approved and is now visible in the marketplace.', 0, '2026-04-30 01:46:22'),
(12, 5, 'Your product kangkong was approved and is now visible in the marketplace.', 0, '2026-04-30 01:46:26'),
(13, 5, 'Your product Apples was approved and is now visible in the marketplace.', 0, '2026-05-02 02:48:21'),
(14, 5, 'New COD order for kangkong. Please confirm the buyer address.', 0, '2026-05-02 04:40:20'),
(15, 4, 'Your order for kangkong was placed. Seller will confirm your address.', 0, '2026-05-02 04:40:20'),
(16, 5, 'Buyer confirmed address for order #6', 0, '2026-05-02 04:40:48'),
(17, 4, 'Your order for kangkong was approved and is being prepared.', 0, '2026-05-02 04:41:47'),
(18, 9, 'Rice was submitted for admin review.', 0, '2026-05-02 04:52:44'),
(19, 9, 'Your product Rice was approved and is now visible in the marketplace.', 0, '2026-05-02 04:52:59'),
(20, 6, 'New complaint #1: order is taking so long', 0, '2026-05-02 04:54:34'),
(21, 7, 'New complaint #1: order is taking so long', 0, '2026-05-02 04:54:34'),
(22, 8, 'New complaint #1: order is taking so long', 0, '2026-05-02 04:54:34'),
(23, 9, 'New COD order for Rice. Please confirm the buyer address.', 0, '2026-05-02 04:54:49'),
(24, 4, 'Your order for Rice was placed. Seller will confirm your address.', 0, '2026-05-02 04:54:49'),
(25, 9, 'Buyer confirmed address for order #7', 0, '2026-05-02 04:54:53'),
(26, 4, 'Your order for Rice was approved and is being prepared.', 0, '2026-05-02 04:58:57'),
(27, 4, 'Tracking updated for order #7: Out for Delivery', 0, '2026-05-02 04:59:32'),
(28, 4, 'New message about order #7', 0, '2026-05-02 05:00:01'),
(29, 4, 'Tracking updated for order #7: Delivered', 0, '2026-05-02 05:03:19'),
(30, 4, 'Your complaint #1 was updated to In Review. Resolution: where getting on it', 0, '2026-05-02 07:18:50'),
(31, 6, 'Rice was edited and needs admin review.', 0, '2026-05-02 08:49:38'),
(32, 7, 'Rice was edited and needs admin review.', 0, '2026-05-02 08:49:38'),
(33, 8, 'Rice was edited and needs admin review.', 0, '2026-05-02 08:49:38'),
(34, 9, 'Rice was updated and sent back for admin review.', 0, '2026-05-02 08:49:38'),
(35, 6, 'kangkong was edited and needs admin review.', 0, '2026-05-02 08:53:29'),
(36, 7, 'kangkong was edited and needs admin review.', 0, '2026-05-02 08:53:29'),
(37, 8, 'kangkong was edited and needs admin review.', 0, '2026-05-02 08:53:29'),
(38, 5, 'kangkong was updated and sent back for admin review.', 0, '2026-05-02 08:53:29'),
(39, 6, 'Apples was edited and needs admin review.', 0, '2026-05-02 08:53:53'),
(40, 7, 'Apples was edited and needs admin review.', 0, '2026-05-02 08:53:53'),
(41, 8, 'Apples was edited and needs admin review.', 0, '2026-05-02 08:53:53'),
(42, 5, 'Apples was updated and sent back for admin review.', 0, '2026-05-02 08:53:53'),
(43, 9, 'Your product Rice was approved and is now visible in the marketplace.', 0, '2026-05-02 08:54:19'),
(44, 9, 'Your product Rice was approved and is now visible in the marketplace.', 0, '2026-05-02 08:54:21'),
(45, 5, 'Your product kangkong was approved and is now visible in the marketplace.', 0, '2026-05-02 08:54:23'),
(46, 5, 'Your product Apples was approved and is now visible in the marketplace.', 0, '2026-05-02 08:54:25'),
(47, 4, 'Your order #6 for kangkong is on the way.', 0, '2026-05-02 09:12:12');

-- --------------------------------------------------------

--
-- Table structure for table `order`
--

DROP TABLE IF EXISTS `order`;
CREATE TABLE IF NOT EXISTS `order` (
  `id` int NOT NULL AUTO_INCREMENT,
  `buyer_id` int DEFAULT NULL,
  `product_id` int DEFAULT NULL,
  `quantity` float DEFAULT NULL,
  `status` varchar(50) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `payment_method` varchar(50) DEFAULT NULL,
  `total_price` float DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `buyer_id` (`buyer_id`),
  KEY `product_id` (`product_id`)
) ENGINE=MyISAM AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `order`
--

INSERT INTO `order` (`id`, `buyer_id`, `product_id`, `quantity`, `status`, `created_at`, `payment_method`, `total_price`) VALUES
(1, 4, 1, 1, 'Approved', '2026-04-25 02:21:31', 'COD', 50),
(2, 4, 1, 1, 'Approved', '2026-04-25 02:29:54', 'COD', 50),
(3, 4, 1, 1, 'Approved', '2026-04-25 02:31:12', 'GCash', 50),
(4, 4, 2, 1, 'Approved', '2026-04-25 04:10:26', 'COD', 25),
(5, 4, 2, 1, 'Approved', '2026-04-25 05:11:28', 'COD', 25),
(6, 4, 1, 1, 'Approved', '2026-05-02 04:40:20', 'COD', 50),
(7, 4, 3, 1, 'Approved', '2026-05-02 04:54:49', 'COD', 100);

-- --------------------------------------------------------

--
-- Table structure for table `orders_order`
--

DROP TABLE IF EXISTS `orders_order`;
CREATE TABLE IF NOT EXISTS `orders_order` (
  `id` int NOT NULL AUTO_INCREMENT,
  `buyer_id` int DEFAULT NULL,
  `product_id` int DEFAULT NULL,
  `quantity` int DEFAULT NULL,
  `total_price` decimal(10,2) DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `buyer_id` (`buyer_id`),
  KEY `product_id` (`product_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `order_delivery`
--

DROP TABLE IF EXISTS `order_delivery`;
CREATE TABLE IF NOT EXISTS `order_delivery` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL,
  `shipping_address` text NOT NULL,
  `contact_number` varchar(50) DEFAULT NULL,
  `status` varchar(80) DEFAULT NULL,
  `tracking_note` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `order_id` (`order_id`)
) ENGINE=MyISAM AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `order_delivery`
--

INSERT INTO `order_delivery` (`id`, `order_id`, `shipping_address`, `contact_number`, `status`, `tracking_note`, `created_at`, `updated_at`) VALUES
(1, 5, 'togbongon P-1', '09518388101', 'Preparing Order', 'Seller approved the order and is preparing it for delivery.', '2026-04-25 05:11:28', '2026-04-25 05:13:38'),
(2, 1, 'togbongon', NULL, 'Address Confirmation', 'Order record created. Please confirm the address with the seller.', '2026-04-25 05:11:58', '2026-04-25 05:11:58'),
(3, 2, 'togbongon', NULL, 'Address Confirmation', 'Order record created. Please confirm the address with the seller.', '2026-04-25 05:11:58', '2026-04-25 05:11:58'),
(4, 3, 'togbongon', NULL, 'Address Confirmation', 'Order record created. Please confirm the address with the seller.', '2026-04-25 05:11:58', '2026-04-25 05:11:58'),
(5, 4, 'togbongon', NULL, 'Address Confirmation', 'Order record created. Please confirm the address with the seller.', '2026-04-25 05:11:58', '2026-04-25 05:11:58'),
(6, 6, 'togbongon', '09633003839', 'Out for Delivery', 'Seller approved the order and is preparing it for delivery.', '2026-05-02 04:40:20', '2026-05-02 09:12:12'),
(7, 7, 'togbongon', '', 'Delivered', 'Seller approved the order and is preparing it for delivery.', '2026-05-02 04:54:49', '2026-05-02 05:03:19');

-- --------------------------------------------------------

--
-- Table structure for table `order_message`
--

DROP TABLE IF EXISTS `order_message`;
CREATE TABLE IF NOT EXISTS `order_message` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL,
  `sender_id` int NOT NULL,
  `receiver_id` int NOT NULL,
  `message` text NOT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `order_id` (`order_id`),
  KEY `sender_id` (`sender_id`),
  KEY `receiver_id` (`receiver_id`)
) ENGINE=MyISAM AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `order_message`
--

INSERT INTO `order_message` (`id`, `order_id`, `sender_id`, `receiver_id`, `message`, `created_at`) VALUES
(1, 5, 5, 4, 'Please confirm your delivery address: togbongon P-1', '2026-04-25 05:11:28'),
(2, 5, 4, 5, 'I confirm that the delivery address is correct.', '2026-04-25 05:11:51'),
(3, 5, 5, 4, 'ok', '2026-04-25 05:13:29'),
(4, 6, 5, 4, 'Please confirm your delivery address: togbongon', '2026-05-02 04:40:20'),
(5, 6, 4, 5, 'I confirm that the delivery address is correct.', '2026-05-02 04:40:48'),
(6, 7, 9, 4, 'Please confirm your delivery address: togbongon', '2026-05-02 04:54:49'),
(7, 7, 4, 9, 'I confirm that the delivery address is correct.', '2026-05-02 04:54:53'),
(8, 7, 9, 4, 'Goodmorning maam Your order is on delivering', '2026-05-02 05:00:01');

-- --------------------------------------------------------

--
-- Table structure for table `order_timeline`
--

DROP TABLE IF EXISTS `order_timeline`;
CREATE TABLE IF NOT EXISTS `order_timeline` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL,
  `status` varchar(80) NOT NULL,
  `note` varchar(255) DEFAULT NULL,
  `actor_id` int DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `order_id` (`order_id`),
  KEY `actor_id` (`actor_id`)
) ENGINE=MyISAM AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `order_timeline`
--

INSERT INTO `order_timeline` (`id`, `order_id`, `status`, `note`, `actor_id`, `created_at`) VALUES
(1, 7, 'Order Placed', 'Order record was created.', 4, '2026-05-02 04:54:49'),
(2, 6, 'Order Placed', 'Order record was created.', 4, '2026-05-02 04:40:20'),
(3, 6, 'Out for Delivery', 'Seller approved the order and is preparing it for delivery.', 5, '2026-05-02 09:12:12');

-- --------------------------------------------------------

--
-- Table structure for table `product`
--

DROP TABLE IF EXISTS `product`;
CREATE TABLE IF NOT EXISTS `product` (
  `id` int NOT NULL AUTO_INCREMENT,
  `farmer_id` int DEFAULT NULL,
  `name` varchar(100) DEFAULT NULL,
  `quantity` float DEFAULT NULL,
  `price` float DEFAULT NULL,
  `description` text,
  `created_at` datetime DEFAULT NULL,
  `image` varchar(200) DEFAULT NULL,
  `unit` varchar(30) DEFAULT 'unit',
  `is_deleted` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `farmer_id` (`farmer_id`)
) ENGINE=MyISAM AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `product`
--

INSERT INTO `product` (`id`, `farmer_id`, `name`, `quantity`, `price`, `description`, `created_at`, `image`, `unit`, `is_deleted`) VALUES
(1, 5, 'kangkong', 99, 50, 'kangkong chips', NULL, '1777712008_WATER-SPINACH_RESIZED1.jpg', 'bundle', 0),
(2, 5, 'Apples', 1000, 25, 'Apples shipped from Bukidnon', NULL, 'BKS5305.jpg', 'piece', 0),
(3, 9, 'Rice', 99, 100, 'A freshly new harvest of Rice in brgy Togbongon', NULL, 'wheat.jpg', 'kg', 0);

-- --------------------------------------------------------

--
-- Table structure for table `products_product`
--

DROP TABLE IF EXISTS `products_product`;
CREATE TABLE IF NOT EXISTS `products_product` (
  `id` int NOT NULL AUTO_INCREMENT,
  `farmer_id` int DEFAULT NULL,
  `name` varchar(100) DEFAULT NULL,
  `quantity` int DEFAULT NULL,
  `price` decimal(10,2) DEFAULT NULL,
  `description` text,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `farmer_id` (`farmer_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `product_rating`
--

DROP TABLE IF EXISTS `product_rating`;
CREATE TABLE IF NOT EXISTS `product_rating` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL,
  `product_id` int NOT NULL,
  `buyer_id` int NOT NULL,
  `farmer_id` int NOT NULL,
  `rating` int NOT NULL,
  `comment` text,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `order_id` (`order_id`),
  KEY `product_id` (`product_id`),
  KEY `buyer_id` (`buyer_id`),
  KEY `farmer_id` (`farmer_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `product_review`
--

DROP TABLE IF EXISTS `product_review`;
CREATE TABLE IF NOT EXISTS `product_review` (
  `id` int NOT NULL AUTO_INCREMENT,
  `product_id` int NOT NULL,
  `status` varchar(50) DEFAULT NULL,
  `admin_note` text,
  `reviewed_by` int DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `product_id` (`product_id`),
  KEY `reviewed_by` (`reviewed_by`)
) ENGINE=MyISAM AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `product_review`
--

INSERT INTO `product_review` (`id`, `product_id`, `status`, `admin_note`, `reviewed_by`, `created_at`, `reviewed_at`) VALUES
(1, 1, 'Approved', 'Product was edited by the seller and needs review again.', 8, '2026-04-29 14:24:57', '2026-05-02 08:54:23'),
(2, 2, 'Approved', 'Product was edited by the seller and needs review again.', 8, '2026-04-29 14:24:57', '2026-05-02 08:54:25'),
(3, 3, 'Approved', 'Product was edited by the seller and needs review again.', 8, '2026-05-02 04:52:44', '2026-05-02 08:54:21');

-- --------------------------------------------------------

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
CREATE TABLE IF NOT EXISTS `user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(100) NOT NULL,
  `role` varchar(50) DEFAULT NULL,
  `password` varchar(200) DEFAULT NULL,
  `location` varchar(200) DEFAULT NULL,
  `disabled` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=MyISAM AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `user`
--

INSERT INTO `user` (`id`, `username`, `role`, `password`, `location`, `disabled`) VALUES
(2, 'ROSS', 'farmer', 'scrypt:32768:8:1$Mu0UJLsVYDFY81x3$2db9193e633e0838772725a87b7649b3f007b5a9e96b5b96db85ba633dc929c4c108524c86dac1fd888f96559c99abdf9cfa85c16e805001c7ebfc0f294ce588', NULL, 0),
(3, 'gian', 'buyer', 'scrypt:32768:8:1$YkPlWsMOywuwXRA5$667a6a36f267217c92c2b929afa0a5f7f267f7de93867b3080d4928094432b4f540a516e1feaaddc9d417e5d28963b2e84f48c3229d80699e1702be637526d50', NULL, 0),
(4, 'jelian', 'buyer', 'scrypt:32768:8:1$ZsGYLAsQcosozxH5$45c1c29830b166825d1a1a8209db010fa0a30eee298282204659a80eae50eb2fcf06d3298ef552a0d18e35f45e7243b11aa91e359204eee7d492f3c091fe7c7e', 'togbongon', 0),
(5, 'mae', 'farmer', 'scrypt:32768:8:1$P6DAU47nriYkjFnC$6b470005ef2faeadbbcbbe096605e02c9799356693eac58b26152724b0a93c4fdd000924b304e627bcf2354ac17e31b9da492d9eeace7c5491df6d1fed061b4d', 'togbongon', 0),
(6, 'vincent', 'admin', 'scrypt:32768:8:1$VjYS8SyxxzZhl7xI$0cb0a09f6768e4595e95ba509c90a25bb4be55835249ad0a1ed965666c03cb514b0fc75959f3b4aff17bd8d9039d4d9da114e0d15bac7296dd9c9fe2c72bf0d1', 'togbongon', 0),
(7, 'giyan', 'admin', 'scrypt:32768:8:1$HSlbqWmn92oFmO6G$74c36549f61885efcfd4df03467cc49d0758483c2895ab32d99ff6f45df5c7dac1edd276e56494ae6a1f05ca8e5d5fbe7efaf75e5b42393c76c522c0c566d644', 'togbongon', 0),
(8, 'admin', 'admin', 'scrypt:32768:8:1$Oz6DKkYVQTwMuWuO$59a6b55fe2a34eb15d2d62a81c06c73c5714635d547b67033344ed9d0b1de6777df53766c58bd126e56b83cf3ac1f41a755409e337cd47fdf45662a3003a6e38', 'Platform Admin', 0),
(9, 'Rozz', 'farmer', 'scrypt:32768:8:1$rRryC5zWCZXUU81y$12534a017252f06da9db418e0a60ab299e7ecc91c04e34dbda54dd6ceafbb30d0f698484c58f3b36ba370e65d29437f049c8bd2ae5a6f0a9a86a3dac0eff2301', 'togbongon', 0);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
